import math
from sympy import *
from latex2sympy2 import latex2sympy

a, b, c, d, i, m, n, o, p, q, r, s, t, x, y, z = symbols('a b c d i m n o p q r s t x y z')

def process_input(input_string):
    try:
        # Try to process input as LaTeX
        input_expr = latex2sympy(input_string)
    except:
        # If not LaTeX, try to process as a regular expression
        input_expr = sympify(input_string)
    return input_expr

def check_answer(user_input, correct_answer_string):
    try:
        # Process user input and correct answer
        user_input_expr = process_input(user_input)
        correct_answer_expr = process_input(correct_answer_string)

        # Simplify the user's input
        user_input_simplified = simplify(user_input_expr)

        # Check if the simplified expression matches the correct answer
        if user_input_simplified.equals(correct_answer_expr):
            return "Correct"
        else:
            if user_input_expr.equals(correct_answer_expr):
                return f"Incorrect - please fully simplify your answer. Correct answer: {correct_answer_string}"
            else:
                return f"Incorrect - your answer is not correct. Correct answer: {correct_answer_string}"

    except:
        return "Invalid input. Please check your syntax."
# Example usage
user_input = r"\frac{dx}{dt} (tx)"
correct_answer = r"t"


#correct_answer = input("correct answer: ")
#user_input = input("answer: ")

print(check_answer(user_input, correct_answer))