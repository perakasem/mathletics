import os
import csv
import asyncio
import sqlite3
import discord
from relayer import Relayer
from db_init import create_db
from typing import Optional
from os.path import join, dirname, abspath
from datetime import datetime
from discord.ext import commands
from graph import graph
from scoring import scoring

nocomp = "No active competitions. Run `!set_comp` to instantiate a competition."

class Comp:
    def __init__(self, name, time, mod, res, path) -> None:
        self.comp_name = datetime.now().strftime('%Y-%m-%d_') + name
        self.mod_channel = mod
        self.res_channel = res
        self.active = False
        self.time = time
        self.db_path = path
        self.plots_path = str(join(dirname(dirname(abspath(__file__))), 'mathletics/plots/current_plot.png'))
        self.competitor = {} # list of competitor channels

class Competition(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.relayer = Relayer(bot)
        self.comp = None

    @commands.command()
    async def set_comp(self, ctx, comp_name=None, time = None, mod_c: Optional[discord.TextChannel] = None, res_c: Optional[discord.TextChannel] = None):
        # error handling
        if hasattr(self, 'comp') or self.comp is not None:
            await ctx.send("Competition already instantiated. Use `!start_comp` to start the competition.")
            return
        if comp_name is None or time is None or mod_c is None or res_c is None:
            await ctx.send("Usage: `!set_comp <competition name> <duration in minutes> <#moderation-channel> <#results channel>`")
            return
        if not isinstance(mod_c, discord.TextChannel) or not isinstance(res_c, discord.TextChannel):
            await ctx.send("Invalid channel(s). Use Discord's typing suggestions to ensure channel validity.")
            return
        if mod_c == res_c:
            await ctx.send("Moderation and results channels must be different.")
            return

        path = str(join(dirname(dirname(abspath(__file__))), f'mathletics/comp_dbs/{comp_name}.db'))
        
        if os.path.exists(path):
            await ctx.send("Competition name taken. Please select a new one.")

        create_db(comp_name)
        await ctx.send(f"Competition {comp_name} created! Moderation will be done in {mod_c.mention} and results will be posted in {res_c.mention}.")
        await ctx.send("Please use `!set_questions <csv>` to add questions and `!set_teams <csv>` to add teams to the competition.")
        self.comp = Comp(comp_name, time, mod_c, res_c, path)

    @commands.command()
    async def start_comp(self, ctx):
        # check if comp is set
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp) 
            return
        if self.comp.active:
            await ctx.send("Competition already active.")
            return

        self.comp.active = True

        # enable message relay from competitor channels to moderation channel
        for channel in self.comp.competitor:
            self.relayer.enable_relay(channel, self.comp.mod_channel)
        
        # display initial leaderboard
        await self.comp.res_channel.purge(limit=5) # clear channel

        graph(self.comp.db_path, self.comp.plots_path)
        leaderboard = discord.File(self.comp.plots_path, filename='leaderboard.png')
        
        embed = discord.Embed(title='Live Leaderboard', color=0xb8eefa)
        embed.set_image(url='attachment://leaderboard.png')
        
        await self.comp.res_channel.send(embed=embed, file=leaderboard)

        os.remove(self.comp.plots_path)

        await ctx.send("Competition started.")
    
    @commands.command()
    async def stop_comp(self, ctx):
        # check if comp is set
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp) 
            return
        if not self.comp.active:
            await ctx.send("Competition has not been started.")
            return

        self.comp.active = False

        # enable message relay from competitor channels to moderation channel
        for channel in self.comp.competitor:
            self.relayer.disable_relay(channel)
        
        # Final Leaderboard Update
        await self.comp.res_channel.purge(limit=5) # clear channel

        graph(self.comp.db_path, self.comp.plots_path)
        leaderboard = discord.File(self.comp.plots_path, filename='leaderboard.png')
        
        embed = discord.Embed(title='Live Leaderboard', color=0xb8eefa)
        embed.set_image(url='attachment://leaderboard.png')
        
        await self.comp.res_channel.send(embed=embed, file=leaderboard)

        os.remove(self.comp.plots_path)

        await self.comp.res_channel.send("The competition has ended. The final results for this section are shown above.")

        await ctx.send("Competition Ended.")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        await self.relayer.on_message(message)
    
    @commands.command()
    async def submit(self, ctx, question):
        if not self.comp.active:
            await ctx.send("Competition has not started.")
            return
        
        while self.comp.active:
            await ctx.send(f"Start question {question}. Enter the question number to confirm or anything character to cancel:")
            def confirm(sender):
                return sender.author == ctx.author and sender.channel == ctx.channel

            try: # waiting for message
                confirmation = await self.bot.wait_for('message', check=confirm, timeout=30.0) 
            except asyncio.TimeoutError: # time out
                await ctx.send("Command timed out.")
                return
            
            if confirmation.content != question: 
                await ctx.send("Command cancelled.")
                return
            
            correct = False
            attempts = 0
            tid = self.comp.competitor.get(ctx.channel)
            time = 0

            conn = sqlite3.connect(self.comp.db_path)
            c = conn.cursor()

            base_score = c.execute("SELECT base_score FROM questions WHERE qid = ?", (question)).fetchone()

            #enter qid, tid 
            exists = c.execute("SELECT * FROM progress WHERE qid = ? AND tid = ?", (question, tid)).fetchone()
            if exists: 
                status = c.execute("SELECT attempts FROM progress WHERE qid = ? AND tid = ?", (question, tid)).fetchone()
                if status == -1:
                    await ctx.send("Question forfeited. Please select a different question.")
                    return
                elif status > 0:
                    await ctx.send("Question already completed.")
                    return
            else: 
                # create row if doesn't exist
                c.execute("INSERT INTO progress (qid, tid, attempts) VALUES (?, ?, 0)", (question, tid))
                conn.commit()
                start_time = datetime.now()
                await ctx.send(f"Timer for question {question} started.")

            while correct is False:

                await ctx.send(f"Enter your answer for question {question}:")

                def verify(sender):
                    return sender.channel == ctx.channel

                response = await self.bot.wait_for('message', check=verify)
                attempts += 1
                
                #if message: skip then BREAK and return, question deemed INCORRECT, cannot be re-attempted (flag: attempts = -1)
                if response.content == 'skip':
                    await ctx.send("You will not be able to re-attempt this question. Enter `y` to skip or any character to cancel skip:")
                    try: # waiting for message
                        response = await self.bot.wait_for('message', check=verify) 
                    except asyncio.TimeoutError: # time out
                        await ctx.send("Command timed out.")
                    
                    if response.content == "y": 
                        attempts = -1
                        await ctx.send("Question forfeited.")
                        break
                
                answer = c.execute("SELECT answer FROM questions WHERE id = ?", (question)).fetchone() # get answer of question
                if response.content == answer:
                    correct = True
                    time = (datetime.now() - start_time).seconds

                    await self.comp.mod_channel.send(f"**Team {tid}:**")
                    await self.comp.mod_channel.send(f"**question**: {question}")
                    await self.comp.mod_channel.send("**result**: correct.")
                    await self.comp.mod_channel.send(f"**attempts**: {attempts}")
                    
                    await ctx.send(f"**question**: {question}")
                    await ctx.send("**result**: correct.")
                    await ctx.send(f"**attempts**: {attempts}")

                else:
                    await self.comp.mod_channel.send(f"**Team {tid}:**")
                    await self.comp.mod_channel.send(f"**question**: {question}")
                    await self.comp.mod_channel.send("**result**: incorrect.")
                    await self.comp.mod_channel.send(f"**attempts**: {attempts}")

                    await ctx.send(f"**question**: {question}")
                    await ctx.send("**result**: incorrect.")
                    await ctx.send(f"**attempts**: {attempts}")

            if attempts < 0:
                # send zero summary
                await self.comp.mod_channel.send(f"**Team {tid} forefeited question {question}**")
                await ctx.send("Question forfeited. You will not be able to re-attempt this question. ")
                await ctx.send(f"**question:** {question}")
                await ctx.send("**score:** 0")

                # send to moderator channels
                c.execute("UPDATE progress SET attempts = ?, time = ? WHERE qid = ? AND tid = ?", (attempts, time, question, tid))
                conn.commit()
                conn.close()
                await ctx.send("Use `!submit <question number>` to start next question.")
                return
            
            score = scoring(attempts, base_score, time)
            completed_q, team_score = c.execute("SELECT completed_qid, score FROM teams WHERE id = ?", (tid)).fetchone()
            new_score = team_score + score
            new_completed_q = completed_q + f"{question}, "
            c.execute("UPDATE teams SET completed_qid = ?, score = ?", (new_completed_q, new_score))
            c.execute("UPDATE progress SET attempts = ?, time = ? WHERE qid = ? AND tid = ?", (attempts, time, question, tid))
            conn.commit()

            # send summary message
            await self.comp.mod_channel.send(f"**Team {tid}:**")
            await self.comp.mod_channel.send("**result:** correct.")
            await self.comp.mod_channel.send(f"**question:** {question}")
            await self.comp.mod_channel.send(f"**attemps:** {attempts}")
            await self.comp.mod_channel.send(f"**score:** {score}")
            await self.comp.mod_channel.send(f"**total score:** {new_score}")

            await ctx.send("**result:** correct.")
            await ctx.send(f"**question:** {question}")
            await ctx.send(f"**attemps:** {attempts}")
            await ctx.send(f"**score:** {score}")
            await ctx.send(f"**total score:** {new_score}")

            # Update leaderboard
            await self.comp.res_channel.purge(limit=5) # clear channel

            graph(self.comp.db_path, self.comp.plots_path)
            leaderboard = discord.File(self.comp.plots_path, filename='leaderboard.png')
            
            embed = discord.Embed(title='Live Leaderboard', color=0xb8eefa)
            embed.set_image(url='attachment://leaderboard.png')
            
            await self.comp.res_channel.send(embed=embed, file=leaderboard)

            os.remove(self.comp.plots_path)

            conn.close()
            
            await ctx.send("Use `!submit <question number>` to start next question.")

            return
        await ctx.send("Competition has Ended.")

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
                except sqlite3.OperationalError as e:
                    await ctx.send("Please attach a correctly formatted questions file.")
                    print(e)
            else:
                await ctx.send("Invalid file type.")
        else:
            await ctx.send("Please attach a valid `.csv` file.")

    @commands.command()
    async def set_teams(self, ctx):
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp) 
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
                except sqlite3.OperationalError as e:
                    await ctx.send("Please attach a correctly formatted teams file.")
                    print(e)
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
    async def competitor(self, ctx, tid):
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp) 
            return

        self.comp.competitor.update({ctx.channel:tid})
        await ctx.send("Competitor channel added")
        return
    
    @commands.command()
    async def remove_competitor(self, ctx):
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp)
            return
        
        if not ctx.channel in self.comp.competitor:
            await ctx.send("Current channel is not a competitor")
            return

        del(self.comp.competitor[ctx.channel])
        await ctx.send("Channel removed from competitors")
        return

async def setup(bot):
    await bot.add_cog(Competition(bot))