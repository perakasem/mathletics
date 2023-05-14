from math import log

# multiply score by a time factor
def time_curve(score, base_score, time):

    # if the time taken is above a dynamic difficulty threshold
    if time > (base_score * 24):

        # the score is multiplied by a curve that accounts for time taken and starts at the threshold
        score = score * ((-(log(time - (24 * base_score - 20)) - 8) / 5))
        return score
    
    # do not multiply if the time is under the threshold
    else:
        return score

# calculate score based on attempts, difficulty, and time
def scoring(attempts, base_score, time):

    # for debugging
    print(f"attempts: {attempts} \nbase: {base_score} \ntime: {time}s")
    
    # subtract base_score/5 each time an incorrect attempt is made
    score = base_score - ((attempts - 1) * (base_score / 5))
    score = time_curve(score, base_score, time)

    # return a minimum score of 1 for a correct answer
    if score < 1:
        return 1
    else: 
        return round(score)

