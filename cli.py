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
        self.scores = {}
        self.questions_taken = set()
        self.questions_completed = set()
        self.incorrect_attempts = {}
        self.start_times = {}
        self.end_times = {}
        
    def total_score(self):
        return sum(self.scores.values())

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
    # if all questions have been taken, return
    if len([team for team in teams if len(team.questions_taken) < len(questions)]) == 0:
        return
    
    # choose team
    update_display(teams, questions) 
    print("Select team or 0 to go back:")
    for i, team in enumerate(teams):
        print(f"{i + 1}. {team}")
    
    try:
        team_index = int(input()) - 1
    except ValueError:
        team_index = None
    
    if team_index == None:
        return
    elif team_index == -1 or team_index > len(teams) - 1:
        return

    # choose question
    update_display(teams, questions)
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
    
    # init score, incorrect attempts, and end time to 0
    teams[team_index].scores[question_index] = 0
    teams[team_index].incorrect_attempts[question_index] = 1
    teams[team_index].end_times[question_index] = 0

def answer_question(teams, questions):
    # if no teams have questions out, return
    if len([team for team in teams if len(team.questions_taken) > 0]) == 0:
        return
    
    # choose team
    update_display(teams, questions)
    print("Select team or 0 to go back:")
    for i, team in enumerate(teams):
        print(f"{i + 1}. {team}")
        
    try:
        team_index = int(input()) - 1
    except ValueError:
        team_index = None
    
    if team_index == None:
        return
    elif team_index == -1 or team_index > len(teams) - 1:
        return

    # choose question
    update_display(teams, questions)
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

    # mark answer
    update_display(teams, questions)
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
        teams[team_index].scores[question_index] += gained_points
        print(f"Points gained: {gained_points}")
        
        # mark question complete
        teams[team_index].questions_taken.remove(question_index)
        teams[team_index].questions_completed.add(question_index)
        teams[team_index].end_times[question_index] = time.time()
    else:
        # add an incorrect attempt
        teams[team_index].incorrect_attempts[question_index] += 1

    input("Press enter to return")
    
def main():
    team_file_path = "mathletics/teams.csv"
    question_file_path = "mathletics/questions.csv"
    teams = configure_teams(team_file_path)
    questions = configure_questions(question_file_path)
    
    while True:
        update_display(teams, questions)
        
        # Print the options
        print("1. Register question taken")
        print("2. Mark answer")
        print("\nEnter to refresh")
        
        choice = input()
        if choice == "":
            update_display(teams, questions)
        elif choice == "1":
            take_question(teams, questions)
        elif choice == "2":
            answer_question(teams, questions)
        else:
            update_display(teams, questions)

# updates leaderboard
def update_display(teams, questions):
    clear_screen()
    
    # TODO: fix this shitty code with a proper leaderboard
    # Print the leaderboard
    print(f"\033[31mLeaderboard:\033[0m")
    print(f"-------------------------")
    print(f"Score\tTeam")
    print(f"-------------------------")
    for team in sorted(teams, key=lambda team: team.total_score(), reverse=True):
        print(f"{team.total_score():03d}\t{team.name}")
    print(f"-------------------------\n")

    # Print the questions currently out
    print(f"\033[36mQuestions Currently Out:\033[0m")
    print(f"-------------------------")
    for count, team in enumerate(teams):
        print(f"{team.name}:")
        for question_index in team.questions_taken:
            question = questions[question_index]
            print(f"{question.question} ({team.incorrect_attempts[question_index]} attempts, {int(time.time() - team.start_times[question_index])} seconds taken so far)")
        print(f"-------------------------\n")
        
    # Print the questions completed:
    print(f"\033[32mQuestions Completed:\033[0m")
    print(f"-------------------------")
    for count, team in enumerate(teams):
        print(f"{team.name}:")
        for question_index in team.questions_completed:
            question = questions[question_index]
            print(f"{question.question} ({team.scores[question_index]} points, {team.incorrect_attempts[question_index]} attempts, {round(team.end_times[question_index] - team.start_times[question_index])} seconds taken)")
        print(f"-------------------------\n")
    

if __name__ == "__main__":
    main()