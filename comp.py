import os
import csv
import asyncio
import sqlite3
import discord
from db_init import create_db
from datetime import datetime
from typing import Optional
from os.path import join, dirname, abspath
from discord.ext import commands
from graph import graph

nocomp = "No active competitions. Run `!set_comp` to instantiate a competition."

class Comp:
    def __init__(self, name, mod, res, path) -> None:
        self.comp_name = datetime.now().strftime('%Y-%m-%d_') + name
        self.mod_channel = mod
        self.res_channel = res
        self.db_path = path
        self.plots_path = str(join(dirname(dirname(abspath(__file__))), 'mathletics/plots/current_plot.png'))
        self.competitor = [] # list of competitor channels



class Competition(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.comp = None

    @commands.command()
    async def set_comp(self, ctx, comp_name=None, mod_c: Optional[discord.TextChannel] = None, res_c: Optional[discord.TextChannel] = None):
        # error handling
        if comp_name is None or mod_c is None or res_c is None:
            await ctx.send("Usage: `!set_comp <competition name> <#moderation-channel> <#results channel>`")
            return
        if not isinstance(mod_c, discord.TextChannel) or not isinstance(res_c, discord.TextChannel):
            await ctx.send("Invalid channel(s). Use Discord's typing suggestions to ensure channel validity.")
            return
        if mod_c == res_c:
            await ctx.send("Moderation and results channels must be different.")
            return

        # add name taken, please choose a different name
        create_db(comp_name)
        path = str(join(dirname(dirname(abspath(__file__))), f'mathletics/comp_dbs/{comp_name}.db'))
        await ctx.send(f"Competition {comp_name} created! Moderation will be done in {mod_c.mention} and results will be posted in {res_c.mention}.")
        await ctx.send("Please use `!set_questions <csv>` to add questions and `!set_teams <csv>` to add teams to the competition.")
        self.comp = Comp(comp_name, mod_c, res_c, path)

    # @commands.command()
    # async def start_comp(self, ctx, mod_c: discord.TextChannel):
    # timer — relay — results updating — referencing databases
    
    # submit answer <question number>
    # response — answer

    @commands.command()
    async def update_mod_channel(self, ctx, mod_c: discord.TextChannel):
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp)
            return
        
        self.comp.mod_channel = mod_c
        await ctx.send(f"moderation channel updated to {mod_c.mention}.")

    @commands.command()
    async def update_res_channel(self, ctx, res_c: discord.TextChannel):
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp)
            return
        
        self.comp.mod_channel = res_c
        await ctx.send(f"moderation channel updated to {res_c.mention}.")

    @commands.command()
    async def set_questions(self, ctx):
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp)
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

                    c.execute("DELETE FROM questions") # clear table

                    for question in questions:
                        c.execute("INSERT INTO questions (id, answer, base_score) VALUES (?, ?, ?)", question)

                    conn.commit()
                    conn.close()

                    await ctx.send("Qeustions set.")
                except:
                    await ctx.send("Please attach a correctly formatted questions file.")
            else:
                await ctx.send("Invalid file type.")
        else:
            await ctx.send("Please attach a valid `.csv` file.")

    @commands.command()
    async def set_teams(self, ctx):
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp)  # Send a response if you want to notify user
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

                    c.execute("DELETE FROM teams") # clear table

                    for team in teams:
                        c.execute("INSERT INTO teams (id, team_name, members, completed_qid, score) VALUES (?, ?, ?, ?, ?)", team)

                    conn.commit()
                    conn.close()

                    await ctx.send("Teams set.")
                except:
                    await ctx.send("Please attach a correctly formatted teams file.")
            else:
                await ctx.send("Invalid file type.")
        else:
            await ctx.send("Please attach a valid `.csv` file.")

    @commands.command()
    async def end_comp(self, ctx):
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp)  # Send a response if you want to notify user
            return
        
        await ctx.send("Type 'end' to end the competition.")

        def verify(sender):
            return sender.author == ctx.author and sender.channel == ctx.channel

        try: # waiting for message
            response = await self.bot.wait_for('message', check=verify, timeout=30.0) 
        except asyncio.TimeoutError: # time out
            await ctx.send("Command timed out.")
            return

        if response.content.lower() != 'end': 
            await ctx.send("Command cancelled.")
            return

        del self.comp
        await ctx.send("Competition ended.")

    @commands.command()
    async def competitor(self, ctx):
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp) 
            return

        self.comp.competitor.append(ctx.channel)
        await ctx.send("Competitor channel added")
        return
    
    # if competitor listed in teams submits answer...
    
    @commands.command()
    async def remove_competitor(self, ctx):
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp)
            return
        
        if not ctx.channel in self.comp.competitor:
            await ctx.send("Current channel is not a competitor")
            return

        self.comp.competitor.remove(ctx.channel)
        await ctx.send("Channel removed from competitors")
        return
    
    # integrate with !start comp and udpate when team scores are updated
    @commands.command()
    async def results(self, ctx):
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp)
            return
        
        # clear channel
        await self.comp.res_channel.purge(limit=5)

        graph(self.comp.db_path, self.comp.plots_path)
        leaderboard = discord.File(self.comp.plots_path, filename='leaderboard.png')
        
        embed = discord.Embed(title='Live Leaderboard', color=0xb8eefa)
        embed.set_image(url='attachment://leaderboard.png')
        
        await self.comp.res_channel.send(embed=embed, file=leaderboard)

        os.remove(self.comp.plots_path)
        return

async def setup(bot):
    await bot.add_cog(Competition(bot))