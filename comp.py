import os, discord, csv, asyncio, sqlite3
from db_init import create_db
from dotenv import load_dotenv
from os.path import join, dirname, abspath
from discord.ext import commands

load_dotenv() # Load variables from .env file

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

class Comp:
    def __init__(self, name, mod_c, res_c, path) -> None:
        self.comp_name = name
        self.mod_channel = mod_c
        self.res_channel = res_c
        self.db_path = path
        self.competitor = []
    # status = active -> allow questions and teams)

@bot.command
async def start_comp(ctx, comp_name, mod_c: discord.TextChannel, res_c: discord.TextChannel):
    """Start a competition with the given name. The competition will be moderated in the mod_channel and results will be posted in the res_channel."""
    create_db(comp_name)
    path = str(join(dirname(dirname(abspath(__file__))), f'mathletics/comp_dbs/{comp_name}.db'))
    await ctx.send(f"Competition {comp_name} created! Moderation will be done in {mod_c.mention} and results will be posted in {res_c.mention}.")
    await ctx.send("Please use `!set_q <csv>` to add questions and `!set_t <csv>` to add teams to the competition.")

    bot.comp = Comp(comp_name, mod_c, res_c, path)

#comp class with all parameters, initialize with start_comp, refer to class for operations. 
@bot.command
async def set_q(ctx):
    try:
        bot.comp
    except:
        return
    
    if bot.comp is None:
        return

    
    if len(ctx.message.attachments) == 1:
        attachment = ctx.message.attachments

        if attachment.filename.endswith('.csv'):
            file = await attachment.read()
            rows = file.decode('utf-8').strip().split('\n')
            questions  = csv.reader(rows)

            conn = sqlite3.connect(bot.comp.db_path)
            c = conn.cursor()

            for question in questions:
                c.execute("INSERT INTO questions (id, answer, base_score) VALUES (?, ?, ?)", question)

            conn.commit()
            conn.close()

        else:
            await ctx.send("invalid file type.")
    else:
        await ctx.send("please attach a valid `.csv` file.")


@bot.command
async def end_comp(ctx):
    await ctx.send("type 'end' to end the competition.")

    def verify(sender):
        return sender.author == ctx.author and sender.channel == ctx.channel

    try: # waiting for message
        response = await bot.wait_for('message', sender=verify, timeout=30.0) # timeout - how long bot waits for message (in seconds)
    except asyncio.TimeoutError: # returning after timeout
        await ctx.send("command timed out.")
        return

    if response.content.lower() != 'end': 
        await ctx.send("command cancelled.")
        return

    del bot.comp
    await ctx.send("competition ended.")

@bot.event
async def competitor(mod_chanel: discord.TextChannel):
    return

