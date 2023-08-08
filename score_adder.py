from scoring import scoring
from random import randint

# base scores for each difficulty level
difficulties = [10, 20, 30]

# RNG for debugging
attempts = randint(1, 5) # 1
time = randint(60, 600) # 200 
base_score = difficulties[randint(0, 2)] # 20

# calculate score
final = scoring(attempts, base_score, time)
print(f"score: {final}")