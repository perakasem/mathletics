import os
import csv
import asyncio
import sqlite3
import discord
from db_init import create_db
from os.path import join, dirname, abspath
from discord.ext import commands
from graph import graph

class Comp:
    def __init__(self, name, mod_c, res_c, path) -> None:
        self.comp_name = name
        self.mod_channel = mod_c
        self.res_channel = res_c
        self.db_path = path
        self.plots_path = str(join(dirname(dirname(abspath(__file__))), 'mathletics/plots/current_plot.png'))
        self.competitor = []
    # status = active -> allow questions and teams)

class Competition(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.comp = None

    @commands.command()
    async def start_comp(self, ctx, comp_name, mod_c: discord.TextChannel, res_c: discord.TextChannel):
        """Start a competition with the given name. The competition will be moderated in the mod_channel and results will be posted in the res_channel."""
        try:
            create_db(comp_name)
            path = str(join(dirname(dirname(abspath(__file__))), f'mathletics/comp_dbs/{comp_name}.db'))
            await ctx.send(f"Competition {comp_name} created! Moderation will be done in {mod_c.mention} and results will be posted in {res_c.mention}.")
            await ctx.send("Please use `!set_q <csv>` to add questions and `!set_t <csv>` to add teams to the competition.")

            self.comp = Comp(comp_name, mod_c, res_c, path)
        except Exception as e:
            await ctx.send("Usage: `!start_comp <competition name> <moderation channel> <results channel>`")

    @commands.command()
    async def set_r(self, ctx):
        try:
            self.comp
        except Exception as e:
            return
        
        if self.comp is None:
            return
        
        if len(ctx.message.attachments) == 1:
            attachment = ctx.message.attachments[0]
            if attachment.filename.endswith('.csv'):
                try:
                    file = await attachment.read()
                    rows = file.decode('utf-8').strip().split('\n')
                    questions  = csv.reader(rows)

                    conn = sqlite3.connect(self.comp.db_path)
                    c = conn.cursor()

                    for question in questions:
                        c.execute("INSERT INTO questions (id, answer, base_score) VALUES (?, ?, ?)", question)

                    conn.commit()
                    conn.close()
                except Exception as e:
                    await ctx.send("please attach a correctly formatted questions file.")
            else:
                await ctx.send("invalid file type.")
        else:
            await ctx.send("please attach a valid `.csv` file.")

    @commands.command()
    async def set_t(self, ctx):
        try:
            self.comp
        except Exception as e:
            return
        
        if self.comp is None:
            return
        
        if len(ctx.message.attachments) == 1:
            attachment = ctx.message.attachments[0]
            if attachment.filename.endswith('.csv'):
                try:
                    file = await attachment.read()
                    rows = file.decode('utf-8').strip().split('\n')
                    teams  = csv.reader(rows)

                    conn = sqlite3.connect(self.comp.db_path)
                    c = conn.cursor()

                    for team in teams:
                        c.execute("INSERT INTO teams (id, team_name, members, completed_qid, score) VALUES (?, ?, ?, ?, ?)", team)

                    conn.commit()
                    conn.close()
                except Exception as e:
                    await ctx.send("please attach a correctly formatted teams file.")
            else:
                await ctx.send("invalid file type.")
        else:
            await ctx.send("please attach a valid `.csv` file.")

    @commands.command()
    async def end_comp(self, ctx):
        await ctx.send("type 'end' to end the competition.")

        def verify(sender):
            return sender.author == ctx.author and sender.channel == ctx.channel

        try: # waiting for message
            response = await self.bot.wait_for('message', check=verify, timeout=30.0) # timeout - how long bot waits for message (in seconds)
        except asyncio.TimeoutError: # returning after timeout
            await ctx.send("command timed out.")
            return

        if response.content.lower() != 'end': 
            await ctx.send("command cancelled.")
            return

        del self.comp
        await ctx.send("competition ended.")

    @commands.command()
    async def competitor(self, mod_chanel: discord.TextChannel):
        return
    
    @commands.command()
    async def results(self, ctx):
        try:
            self.comp
        except Exception as e:
            return
        
        if self.comp is None:
            return
        
        # clear channel
        await self.comp.res_channel.purge(limit=5)

        graph(self.comp.db_path, self.comp.plots_path)
        leaderboard = discord.File(self.comp.plots_path, filename='leaderboard.png')
        
        embed = discord.Embed(title='Live Leaderboard', color=0xb8eefa)
        embed.set_image(url='attachment://leaderboard.png')
        
        await self.comp.res_channel.send(embed=embed, file=leaderboard)

        os.remove(self.comp.plots_path)