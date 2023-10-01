import sqlite3
from os.path import join, dirname, abspath
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager

font_path = str(join(dirname(dirname(abspath(__file__))), 'mathletics/assets/ggsans-Bold.ttf'))  # replace this with the path to your font file
font = font_manager.FontProperties(fname=font_path)

def graph(path, save_path):
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

    # plot data
    plt.barh(sorted_teams, sorted_scores, color='#89CADF')
    
    for index, value in enumerate(sorted_scores):
        plt.text(value + (0.05 * max(sorted_scores)), 
                index, str(value), 
                color='#B8EEFA', 
                verticalalignment='center', 
                fontsize=20,
                fontproperties=font)

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
    plt.xlim(0, max(scores) * 1.2)

    plt.savefig(save_path, transparent=True)
    plt.close()