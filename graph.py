"""
Module to generate live leaderboard graphs for competitions.

Dependencies:
    sqlite3: Used for querying competitor scores
    os.path: Standard Python library functions for file and directory path manipulations.
    matplotlib.pyplot: Used for generating bar graph
    matplotlib.font_manager: Used to manage custom fonts in plots

Example:
    To use the graph function, import it into your file:
    
    ```python
    from graph import graph
    ```
"""

import sqlite3
from os.path import join, dirname, abspath
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager

# font file path setup
font_path = str(join(dirname(dirname(abspath(__file__))), 'mathletics/assets/ggsans-Bold.ttf'))
font = font_manager.FontProperties(fname=font_path)


def graph(path: str, save_path: str) -> None:
    """Generates leaderboard bar graph.

    Args:
        path (str): Path to competition database used for accesing points.
        save_path (str): Path to graph folder used for saving leaderboards.
    """
    conn = sqlite3.connect(path)
    conn.row_factory = lambda cursor, row: row[0]
    c = conn.cursor()

    teams = c.execute("SELECT team_name FROM teams").fetchall()
    scores = c.execute("SELECT score FROM teams").fetchall()

    conn.close()
    
    # turn parallel lists into dict and sort by scores
    sorted_results = sorted(zip(teams, scores), key=lambda pair: pair[1])

    # revert to lists
    sorted_teams, sorted_scores = zip(*sorted_results)

    _, ax = plt.subplots(figsize=(8, 6))
    
    # generate bar charts and save files
    plt.barh(sorted_teams, sorted_scores, color='#89CADF')
    
    # plot the score next to each bar
    for index, value in enumerate(sorted_scores):
        plt.text(value + (0.05 * max(sorted_scores)), 
                index, str(value), 
                color='#B8EEFA', 
                verticalalignment='center', 
                fontsize=20,
                fontproperties=font)

    # cosmetic configuration
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(left=False, bottom=False, labelbottom=False)
    ax.set_yticklabels(sorted_teams, fontproperties=font, color='#B8EEFA')
    ax.set_yticks(range(len(sorted_teams)))
    ax.tick_params(axis='y', labelsize=20, direction='out', pad=(10))
    title = ax.set_title("LEADERBOARD", fontproperties=font, color='#B8EEFA', fontsize=20, loc='center')
    title.set_position([0, 1.05])
    
    plt.subplots_adjust(left=0.3, top=0.8)
    plt.xlim(0, max(sorted_scores) * 1.2)

    # save graph as png to temporary location
    plt.savefig(save_path, transparent=True)
    plt.close()