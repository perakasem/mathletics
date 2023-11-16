"""
Module to calculate score of answer submissions.

Dependencies:
    math: Stanfard Python library for mathematical functions

Example:
    To use the scoring function, import it into your bot's file:
    
    ```python
    from scoring import scoring
    ```
"""

from math import log

def scoring(attempts: int, base_score: int, time: int) -> int:
    """Calculates score received upon submitting a question.

    Args:
        attempts (int): Name of database to be used as the filename.
        base_score (int): Maximum achievable score of question.
        time (int): Time taken to complete questions in seconds.

    Returns: 
        score (int): calculated score
    """
    print(f"attempts: {attempts} \nbase: {base_score} \ntime: {time}s") # print input for debugging
    threshold = base_score * 24 # assign dynamic scoring scale threshold
    
    # algorithm: subtract base_score/5 each time an incorrect attempt is made
    score = base_score - ((attempts - 1) * (base_score / 5))
    
    # if the time taken is above the scoring threshold
    if time > threshold:

        # the score is multiplied by a curve that accounts for time taken and starts at the specified threshold
        score = score * ((-(log(time - (threshold - 20)) - 8) / 5))

    # return a minimum score of 1 for a correct answer or a rounded score
    if score < 1:
        return 1
    else: 
        return round(score)
