import sys
import os
import time
import csv
from math import log

class Team:
    """
    Represents one team of compeitiors in the competition.
    """    
    def __init__(self, name):
        self.name = name
        self.members = []
        self.score = 0
        self.incorrect_attempts = 0
        self.questions_taken = set()
        self.start_times = {}

    def add_member(self, member):
        self.members.append(member)

    def __str__(self):
        return self.name

class Question:
    """
    Represents one question in the competition
    """    
    def __init__(self, question, answer, base_score):
        self.question = question
        self.answer = answer
        self.base_score = base_score

# returns the score based on attempt details
def scoring(attempts, base_score, time): 
    # subtract base_score/5 each time an incorrect attempt is made
    score = base_score - ((attempts - 1) * (base_score / 5))
    
    # if the time taken is above a dynamic difficulty threshold
    if time > (base_score * 24):
        # the score is multiplied by a curve that accounts for time taken and starts at the threshold
        score = score * ((-(log(time - (24 * base_score - 20)) - 8) / 5))
    
    # min score is 1.
    return max(round(score), 1)

# helper function to clear the terminal
clear_screen = lambda: os.system('cls' if os.name == 'nt' else 'clear')

# reads team info from csv
def configure_teams(file_path):
    clear_screen()
    team_list = []
    with open(file_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            team_name = row[0]
            team = Team(team_name)
            for member in row[1:]:
                team.add_member(member)
            team_list.append(team)
    return team_list

# reads questions info from csv
def configure_questions(file_path):
    clear_screen()
    question_list = []
    with open(file_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            question = row[0]
            answer = row[1]
            base_score = int(row[2])
            question_list.append(Question(question, answer, base_score))
    return question_list

# for when a team takes a question
def take_question(teams, questions):
    clear_screen()
    print("Select team or 0 to go back:")
    for i, team in enumerate(teams):
        print(f"{i + 1}. {team}")
    team_index = int(input()) - 1
    
    if team_index == -1:
        return

    clear_screen()
    print("Select question:")
    for i, question in enumerate(questions):
        if i not in teams[team_index].questions_taken:
            print(f"{i + 1}. {question.question}")
    question_index = int(input()) - 1

    # keep track of start time and add the question to that team's list
    teams[team_index].questions_taken.add(question_index)
    teams[team_index].start_times[question_index] = time.time()

def answer_question(teams, questions):
    clear_screen()
    print("Select team or 0 to go back:")
    for i, team in enumerate(teams):
        print(f"{i + 1}. {team}")
    team_index = int(input()) - 1
    
    if team_index == -1:
        return

    clear_screen()
    # if the team has no questions taken, return
    if len(teams[team_index].questions_taken) == 0:
        print("This team has no questions taken")
        return
    
    # otherwise, show the list of questions currently taken
    print("Select question:")
    for i, question in enumerate(questions):
        if i in teams[team_index].questions_taken:
            print(f"{i + 1}. {question.question}")
    question_index = int(input()) - 1

    clear_screen()
    print(f"Markscheme: {questions[question_index].answer}")
    print("Is the answer correct? (y/n)")
    correct = input().lower() == 'y'
    if correct:
        # calculate the time taken 
        time_taken = int(time.time() - teams[team_index].start_times[question_index])
        print(f"Time taken: {time_taken} seconds")
        
        # calculate the score
        gained_points = scoring(teams[team_index].incorrect_attempts, questions[question_index].base_score, time_taken)
        teams[team_index].score += gained_points
        print(f"Points gained: {gained_points}")
        
        # remove the question from the list of questions taken
        teams[team_index].questions_taken.remove(question_index)
    else:
        # add an incorrect attempt
        teams[team_index].incorrect_attempts += 1

    input("Press enter to return")
    
def main():
    team_file_path = "teams.csv"
    question_file_path = "questions.csv"
    teams = configure_teams(team_file_path)
    questions = configure_questions(question_file_path)

    while True:
        clear_screen()
        print("1. Take a question")
        print("2. Answer a question")
        print("3. Exit")
        choice = int(input())

        if choice == 1:
            take_question(teams, questions)
        elif choice == 2:
            answer_question(teams, questions)
        elif choice == 3:
            sys.exit()

if __name__ == "__main__":
    main()