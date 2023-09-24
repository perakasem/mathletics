import sqlite3
from os.path import join, dirname, abspath

def create_db(name):
    db_path = str(join(dirname(dirname(abspath(__file__))), f'mathletics/comp_dbs/{name}.db'))
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # create a table for questions
    c.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY,
            answer TEXT,
            base_score INTEGER
        )
    ''')

    # create a table for question logging
    c.execute('''
        CREATE TABLE IF NOT EXISTS progress (
            qid INTEGER,
            tid INTEGER,
            attempts INTEGER,
            time INTEGER,
            completed integer DEFAULT 0
        )
    ''')

    # create a table for teams
    # members and completed_questions stores lists as JSON strings
    c.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY,
            team_name TEXT,
            members TEXT,
            completed_qid TEXT,
            score INTEGER
        )
    ''')

    conn.commit()
    conn.close()

create_db("test")