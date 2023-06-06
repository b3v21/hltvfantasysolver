from gurobipy import *
import math
from data import Players, Boosters, Roles, Games, WP, Rating, Price

## SETS ##
# P - Set of Players
# T - Sets of Teams, (Subsets of players)
# R - Roles a player can take
# B - Boosters that can be given to a player
# G - Set of games that are played

## DATA ##
# R6_p - Player Rating (HLTV 2.0) over last 6m (for p in P)
# R3_p - Player Rating (HLTV 2.0) over last 3m (for p in P)
# R1_p - Player Rating (HLTV 2.0) over last 1m (for p in P)
# T_p - Player's Team (P_t elem of T) (for p in P)
# P_p - Player's Price (for p in P)
# R6W - Weighting of 6m rating
# R3W - Weighting of 3m rating
# R1W - Weighting of 1m rating
# R_p - Role trigger % (big / small) (for p in P)
# B_p - Booster trigger % (big / small) (for p in P)

## VARIABLES ##
# X_p (BINARY)          = 1 if player p is selected to be on the team
#                       = 0 otherwise
# Y_{p, r} (BINARY)     = 1 if role r is assigned to player p
#                       = 0 otherwise
# Z_{p, b, g} (BINARY)  = 1 if player p is assigned booster b for game g
#                       = 0 otherwise

## OBJECTIVE FUNCTION ##
# Maximise the weighted average of R6,R3,R1 across the whole team
# REVISED: Maximise the number of expected points scored across all games

## CONSTRAINTS ##
# * Two players maximum from each team
# * Budget of $1,000,000
# * Team has 5 players
# * Player can only appear in the team once

# * Each booster can only be applied once
# * Each role can only be assigned once
# * Each player can only have 1 role

# Play around with these
R6W = 0.2
R1W = 0.8

# Set sizes
P = range(len(Players))
B = range(len(Boosters[0]))
G = range(len(Games))
R = range(len(Roles[0]))

m = Model("HLTV FANTASY")

# Variables
X = {p: m.addVar(vtype=GRB.BINARY) for p in P}
Y = {(p, r): m.addVar(vtype=GRB.BINARY) for p in P for r in R}
Z = {(p, b, g): m.addVar(vtype=GRB.BINARY) for p in P for b in B for g in G}

# Objective Function
m.setObjective(
    quicksum(X[p] * (((R1W * Rating[p][0]) + (R6W * Rating[p][1])) - 1) * 50 for p in P)
    * len(Games)
    + quicksum(Z[p, b, g] * Boosters[p][b][1] * 5 for p in P for g in G for b in B)
    + (
        quicksum(Y[p, r] * Roles[p][r][1] * 2 for p in P for r in R)
        + quicksum(Y[p, r] * Roles[p][r][2] * 5 for p in P for r in R)
        - quicksum(
            Y[p, r] * (1 - Roles[p][r][1] - Roles[p][r][2]) * 2 for p in P for r in R
        )
    )
    * len(Games)
    + quicksum(X[p] * WP[math.floor(p / 5)] * 6 for p in P) * len(Games)
    - quicksum(X[p] * (1 - WP[math.floor(p / 5)]) * 3 for p in P) * len(Games),
    GRB.MAXIMIZE,
)

# EXPECTED RATING (rating - 1 * 50) +
# EXPECTED BOOSTER POINTS (5 points if triggered) +
# EXPECTED ROLE POINTS (+/-2 if triggered, +5 if BIG triggered) +
# EXPECTED WIN / LOSS POINTS (-3 for loss, +6 for win)

# Constraints
# * Two players maximum from each team
# * Budget of $1,000,000
# * Team has 5 players

# * Each booster can only be applied once
# * Each role can only be assigned once
# * Each player can only have 1 role

# Each team can only provide max 2 players
for t in set(x[1] for x in Players):
    m.addConstr(quicksum(X[p] for p in P if Players[p][1] == t) <= 2)

# Maximum buget of 1,000,000
m.addConstr(quicksum(X[p] * Price[p] for p in P) <= 1000000)

# 5 Players on a team
m.addConstr(quicksum(X[p] for p in P) == 5)

# Every booster can only be used once
for b in B:
    m.addConstr(quicksum(Z[p, b, g] for p in P for g in G) <= 1)
    for g in G:
        m.addConstr(quicksum(Z[p, b, g] for p in P) <= 1)

for p in P:
    for g in G:
        m.addConstr(quicksum(Z[p, b, g] for b in B) <= 1)

# Every role can only be used once
for r in R:
    m.addConstr(quicksum(Y[p, r] for p in P) <= 1)

# Each player can only have 1 role
for p in P:
    m.addConstr(quicksum(Y[p, r] for r in R) <= 1)

# A player can only have a booster if the player is on the team
for g in G:
    for b in B:
        for p in P:
            m.addConstr(Z[p, b, g] <= X[p])

# A player can only have a role if the player is on the team
for r in R:
    for p in P:
        m.addConstr(Y[p, r] <= X[p])

# Can't select Sonic as his role stats aren't filled in
m.addConstr(X[27] == 0)


m.optimize()

print("\n")
for g in G:
    print(f"DAY {g + 1}")
    for p in P:
        if X[p].x == 1:
            for r in R:
                if Y[p, r].x == 1:
                    for b in B:
                        if Z[p, b, g].x == 1:
                            print(
                                Players[p],
                                "used role",
                                Roles[p][r][0],
                                Roles[p][r][1:3],
                                "and booster",
                                Boosters[p][b][0],
                                f"({Boosters[p][b][1]})",
                            )
                    if sum(Z[p, b, g].x for b in B) == 0:
                        print(
                            Players[p],
                            "used role",
                            Roles[p][r][0],
                            Roles[p][r][1:3],
                            "and no booster",
                        )

print("\n")
print("Total Price:", sum(X[p].x * Price[p] for p in P if X[p].x == 1))
print("Expected Pointscore:", m.ObjVal)
print("\n")
