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
        self.questions_taken = set()
        self.incorrect_attempts = {}
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
    
    try:
        team_index = int(input()) - 1
    except ValueError:
        team_index = None
    
    if team_index == None:
        return
    elif team_index == -1 or team_index > len(questions) - 1:
        return

    clear_screen()
    print("Select question:")
    for i, question in enumerate(questions):
        if i not in teams[team_index].questions_taken:
            print(f"{i + 1}. {question.question}")
    
    try:
        question_index = int(input()) - 1
    except ValueError:
        question_index = None
    
    if question_index == None:
        return
    elif question_index == -1 or question_index > len(questions) - 1:
        return

    # keep track of start time and add the question to that team's list
    teams[team_index].questions_taken.add(question_index)
    teams[team_index].start_times[question_index] = time.time()
    
    # init the incorrect attempts to 0
    teams[team_index].incorrect_attempts[question_index] = 0

def answer_question(teams, questions):
    # if no teams have questions out, return
    if len([team for team in teams if len(team.questions_taken) > 0]) == 0:
        return
    
    clear_screen()
    print("Select team or 0 to go back:")
    for i, team in enumerate(teams):
        print(f"{i + 1}. {team}")
        
    try:
        team_index = int(input()) - 1
    except ValueError:
        team_index = None
    
    if team_index == None:
        return
    elif team_index == -1 or team_index > len(questions) - 1:
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

    try:
        question_index = int(input()) - 1
    except ValueError:
        question_index = None
    
    if question_index == None:
        return
    elif question_index == -1 or question_index > len(questions) - 1:
        return

    clear_screen()
    print(f"Markscheme: {questions[question_index].answer}")
    print("Is the answer correct? (y/n)")
    correct = input().lower() == 'y'
    if correct:
        # calculate the time taken 
        time_taken = int(time.time() - teams[team_index].start_times[question_index])
        print(f"Time taken: {time_taken} seconds")
        
        # prior attemps
        print(f"Prior attempts: {teams[team_index].incorrect_attempts[question_index]}")
        
        # calculate the score
        gained_points = scoring(teams[team_index].incorrect_attempts[question_index], questions[question_index].base_score, time_taken)
        teams[team_index].score += gained_points
        print(f"Points gained: {gained_points}")
        
        # remove the question from the list of questions taken
        teams[team_index].questions_taken.remove(question_index)
    else:
        # add an incorrect attempt
        teams[team_index].incorrect_attempts[question_index] += 1

    input("Press enter to return")
    
def main():
    team_file_path = "teams.csv"
    question_file_path = "questions.csv"
    teams = configure_teams(team_file_path)
    questions = configure_questions(question_file_path)
    
    update_display(teams, questions)

def update_display(teams, questions):
    while True:
        clear_screen()
        # TODO: fix this shitty code with a proper leaderboard
        # Print the leaderboard
        print(f"\033[31mLeaderboard:\033[0m")
        print(f"-------------------------")
        print(f"Team\t\tScore")
        print(f"-------------------------")
        for team in sorted(teams, key=lambda team: team.score, reverse=True):
            print(f"{team.name}\t\t{team.score}")
        print(f"-------------------------\n")

        # Print the questions currently out
        print(f"\033[36mQuestions Currently Out:\033[0m")
        print(f"-------------------------")
        for count, team in enumerate(teams):
            print(f"{team.name}:")
            for question_index in team.questions_taken:
                question = questions[question_index]
                print(f"{question.question} ({team.incorrect_attempts[question_index]} attempts, {int(time.time() - team.start_times[question_index])} seconds taken so far)")
            print(f"-------------------------")

        # Print the options
        print("\n1. Register question taken")
        print("2. Mark answer")
        print("\nAny key to refresh")
        
        choice = input()
        if choice == "":
            update_display(teams, questions)
        elif int(choice) == 1:
            take_question(teams, questions)
        elif int(choice) == 2:
            answer_question(teams, questions)

if __name__ == "__main__":
    main()