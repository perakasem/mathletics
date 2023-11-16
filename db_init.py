"""
Module to create the competition database.

Dependencies:
    sqlite3: Used for managing sqlite databases
    os.path: Standard Python library functions for file and directory path manipulations.

Example:
    To use the create_db function, import it into your bot's file:
    
    ```python
    from db_init import create_db
    ```
"""

import sqlite3
from os.path import join, dirname, abspath

def create_db(name: str):
    """Creates an SQLite database for the current competition

    Args:
        name (str): name of database to be used as the filename
    """
    db_path = str(join(dirname(dirname(abspath(__file__))), f'mathletics/comp_dbs/{name}.db'))
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Questions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY,
            answer TEXT,
            base_score INTEGER
        )
    ''')

    # Progress table (stores instances of question completion)
    c.execute('''
        CREATE TABLE IF NOT EXISTS progress (
            qid INTEGER,
            tid INTEGER,
            attempts INTEGER,
            time INTEGER,
            completed integer DEFAULT 0
        )
    ''')

    # Teams table
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