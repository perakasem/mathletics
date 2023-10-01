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
    def __init__(self, name, mod, res, path) -> None:
        self.comp_name = name
        self.mod_channel = mod
        self.res_channel = res
        self.active = False
        self.db_path = path
        self.plots_path = str(join(dirname(dirname(abspath(__file__))), 'mathletics/plots/current_plot.png'))
        self.competitor = {} # list of competitor channels
        self.submitting_channels = set()

class Competition(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.relayer = Relayer(bot)
        self.comp = None

    @commands.command()
    async def hello(self, ctx):
        await ctx.send("Hello! I am Mathletics Steward. Use `!help` to access commands, or contact the administrator to learn more.")

    @commands.command()
    @commands.has_role('Invigilator')
    async def status(self, ctx):
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send("Competition has not started.") 
            return
        embed = discord.Embed(title="Status", description=f"Competition: {self.comp.comp_name}", color=0xb8eefa)  # 0x00ff00 is a green color for "correct"
        embed.add_field(name="moderation channel", value=f"{self.comp.mod_channel}", inline=True)
        embed.add_field(name="results channel", value=f"{self.comp.res_channel}", inline=True)
        embed.add_field(name="active", value=f"{self.comp.active}", inline=True)
        for pair in self.comp.competitor:
            embed.add_field(name="competitors", value=f"{pair}", inline=True)
        await ctx.send(embed=embed)
        
    @commands.command()
    @commands.has_role('Invigilator')
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
        
        comp_name = datetime.now().strftime('%Y-%m-%d_') + comp_name

        path = str(join(dirname(dirname(abspath(__file__))), f'mathletics/comp_dbs/{comp_name}.db'))

        if os.path.exists(path):
            await ctx.send("Competition name taken. Please select a new one.")
            return
        
        self.comp = Comp(comp_name, mod_c, res_c, path)
        create_db(comp_name)

        await ctx.send(f"Competition {comp_name} created! Moderation will be done in {mod_c.mention} and results will be posted in {res_c.mention}.")
        await ctx.send("Please use `!set_questions <csv>` to add questions and `!set_teams <csv>` to add teams to the competition.")
    
    @commands.command()
    @commands.has_role('Invigilator')
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
            await self.relayer.enable_relay(channel, self.comp.mod_channel)
            channel_obj = self.bot.get_channel(channel)
            await channel_obj.send("The competition has started. Use `!submit <question number>` to start a question.")
        
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
    @commands.has_role('Invigilator')
    async def stop_comp(self, ctx):
        # check if comp is set
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp) 
            return
        if not self.comp.active:
            await ctx.send("Competition has not been started.")
            return

        # enable message relay from competitor channels to moderation channel
        for channel in self.comp.competitor:
            await self.relayer.disable_relay(channel)
            channel_obj = self.bot.get_channel(channel)

            embed = discord.Embed(title="Question Overview", description=f"**The competition has ended. Congratulations on your results. You can view the leaderboard in {self.comp.res_channel.mention}.**", color=0xffff00)
            await channel_obj.send(embed=embed)

        self.comp.active = False
        
        # Final Leaderboard Update
        await self.comp.res_channel.purge(limit=5) # clear channel

        # SEND PROGRESS TABLE in EMBED, SEND EACH TEAM'S SUMMARY IN A SEPARATE EMBED, SORT BY QUESTION NUMBER, DISPLAY QUESTION NUMBER, ATTEMPTS, TIME TAKEN, AND SCORE FOR EACH QUESTION. DISPLAY 'FORFEITED' IF ATTEMPTS IS LESS THAN ZERO. 

        graph(self.comp.db_path, self.comp.plots_path)
        leaderboard = discord.File(self.comp.plots_path, filename='leaderboard.png')
        
        embed = discord.Embed(title='Live Leaderboard', color=0xb8eefa)
        embed.set_image(url='attachment://leaderboard.png')
        
        await self.comp.res_channel.send(embed=embed, file=leaderboard)

        os.remove(self.comp.plots_path)

        await self.comp.res_channel.send("The competition has ended. The final results for this section are shown above.")

        await ctx.send("Competition Stopped.")
    
    @commands.command()
    async def submit(self, ctx, question):
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send("Competition has not started.") 
            return

        if not self.comp.active:
            await ctx.send("Competition has not started.")
            return
        
        if ctx.channel.id in self.comp.submitting_channels:
            await ctx.send("The command is currently running in this channel! Please wait.")
            return
        
        while self.comp.active:
            correct = False
            attempts = 0

            tid = self.comp.competitor.get(ctx.channel.id)
            time = 0

            conn = sqlite3.connect(self.comp.db_path)
            c = conn.cursor()            
            base_score = c.execute("SELECT base_score FROM questions WHERE id = ?", (question)).fetchone()[0]
            
            question_row = c.execute("SELECT * FROM questions WHERE id = ?", (question)).fetchone()
            if question_row:
                question_exists = question_row[0]
            else:
                question_exists = None
            if question_exists is None:
                await ctx.send("**Chosen question does not exist!**")
                return

            embed = discord.Embed(title="Question Overview", description=f"Question: {question}", color=0xb8eefa)
            embed.add_field(name="Maximum Achievable Score", value=f"{base_score}", inline=True)
            await ctx.send(embed=embed)

            await ctx.send(f"Enter the question number to start question {question} or any character to cancel:")

            def confirm(sender):
                return sender.author == ctx.author and sender.channel == ctx.channel

            try: # waiting for message
                confirmation = await self.bot.wait_for('message', check=confirm, timeout=30.0) 
            except asyncio.TimeoutError: # time out
                await ctx.send("Command timed out.")
                return
            
            if confirmation.content != question: 
                await ctx.send("Question cancelled.")
                return

            q_exists = c.execute("SELECT * FROM questions WHERE id = ?", (question)).fetchone()[0]
            if not q_exists: 
                await ctx.send("Question does not exist.")
                return

            #enter qid, tid 
            row = c.execute("SELECT * FROM progress WHERE qid = ? AND tid = ?", (question, tid)).fetchone()
            if row:
                exists = row[0]
            else:
                exists = None
            if exists: 
                status = c.execute("SELECT attempts FROM progress WHERE qid = ? AND tid = ?", (question, tid)).fetchone()[0]
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

                await ctx.send(f"Enter your answer for question {question} or `skip` to forfeit:")

                def verify(sender):
                    return sender.channel == ctx.channel

                response = await self.bot.wait_for('message', check=verify)

                if response.content.startswith('!'):
                    await ctx.send("Answer cannot begin with `!`")
                    await ctx.send("This response will not affect your attempts.")
                    attempts -= 1

                attempts += 1
                
                #if message: skip then BREAK and return, question deemed INCORRECT, cannot be re-attempted (flag: attempts = -1)
                if response.content == 'skip':
                    await ctx.send("You will not be able to re-attempt this question. Enter `y` to skip or any character to cancel skip:")
                    try: # waiting for message
                        response = await self.bot.wait_for('message', check=verify) 
                    except asyncio.TimeoutError: # time out
                        await ctx.send("Command timed out.")
                        attempts -= 1
                    
                    if response.content == "y": 
                        attempts = -1 
                        await ctx.send("Question forfeited.")
                        break
                    else:
                        attempts -= 1
                
                answer = c.execute("SELECT answer FROM questions WHERE id = ?", (question)).fetchone()[0] # get answer of question
                if response.content == answer:
                    correct = True
                    time = (datetime.now() - start_time).seconds

                    embed = discord.Embed(title="Submission Results", description=f"Question: {question}", color=0x00ff00)  # 0x00ff00 is a green color for "correct"
                    embed.add_field(name="Result", value="Correct", inline=True)
                    embed.add_field(name="Attempts", value=f"{attempts}", inline=True)
                    embed.add_field(name="Time", value=f"{time}", inline=True)
                    await ctx.send(embed=embed)

                    mod_embed = discord.Embed(title=f"Team {tid}", description=f"Question {question} Submission Results", color=0x00ff00)  # Green for "correct"
                    mod_embed.add_field(name="Result", value="Correct", inline=True)
                    mod_embed.add_field(name="Attempts", value=f"{attempts}", inline=True)
                    mod_embed.add_field(name="Time", value=f"{time}", inline=True)
                    await self.comp.mod_channel.send(embed=mod_embed)

                else:
                    time = (datetime.now() - start_time).seconds

                    embed = discord.Embed(title="Submission Results", description=f"Question: {question}", color=0xff0000)  # 0xff0000 is red for "incorrect"
                    embed.add_field(name="Result", value="Incorrect", inline=True)
                    embed.add_field(name="Attempts", value=str(attempts), inline=True)
                    embed.add_field(name="Elapsed Time", value=f"{time} seconds", inline=True)
                    await ctx.send(embed=embed)

                    mod_embed = discord.Embed(title=f"Team {tid}", description=f"Question {question} Submission Results", color=0xff0000)  # 0xff0000 is red, representing "incorrect"
                    mod_embed.add_field(name="Result", value="Incorrect", inline=False)
                    mod_embed.add_field(name="Attempts", value=str(attempts), inline=True)
                    mod_embed.add_field(name="Elapsed Time", value=f"{time} seconds", inline=True)
                    await self.comp.mod_channel.send(embed=mod_embed)

            if attempts < 0:
                # send zero summary
                await self.comp.mod_channel.send(f"**Team {tid} forefeited question {question}**")

                embed = discord.Embed(title="Question Forfeited", description=f"Question: {question}", color=0xff6600)  # 0xff6600 is an orange-ish color for "forfeit"
                embed.add_field(name="Score", value="0", inline=True)
                await ctx.send(embed=embed)

                # send to moderator channels
                c.execute("UPDATE progress SET attempts = ?, time = ? WHERE qid = ? AND tid = ?", (attempts, time, question, tid))
                conn.commit()
                conn.close()
                await ctx.send("Use `!submit <question number>` to start next question.")
                return
            
            score = scoring(attempts, base_score, time)
            completed_q, team_score = c.execute("SELECT completed_qid, score FROM teams WHERE id = ?", (tid,)).fetchone()
            new_score = team_score + score
            new_completed_q = completed_q + f"{question}, "
            c.execute("UPDATE teams SET completed_qid = ?, score = ? WHERE id = ?", (new_completed_q, new_score, tid))
            c.execute("UPDATE progress SET attempts = ?, time = ? WHERE qid = ? AND tid = ?", (attempts, time, question, tid))
            conn.commit()

            # send summary message
            embed = discord.Embed(title="Result", description=f"Question {question} Summary", color=0xb8eefa)
            embed.add_field(name="Result", value="Correct", inline=False)
            embed.add_field(name="Question", value=str(question), inline=True)
            embed.add_field(name="Attempts", value=str(attempts), inline=True)
            embed.add_field(name="Score", value=str(score), inline=True)
            embed.add_field(name="Total Score", value=str(new_score), inline=True)
            await ctx.send(embed=embed)

            # send to mod channel
            mod_embed = discord.Embed(title=f"Team {tid}", description=f"Question {question} Summary", color=0xb8eefa)
            mod_embed.add_field(name="Result", value="Correct", inline=False)
            mod_embed.add_field(name="Question", value=str(question), inline=True)
            mod_embed.add_field(name="Attempts", value=str(attempts), inline=True)
            mod_embed.add_field(name="Score", value=str(score), inline=True)
            mod_embed.add_field(name="Total Score", value=str(new_score), inline=True)
            await self.comp.mod_channel.send(embed=mod_embed)

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
    @commands.has_role('Invigilator')
    async def update_mod_channel(self, ctx, mod_c: discord.TextChannel):
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp)
            return
        
        self.comp.mod_channel = mod_c
        await ctx.send(f"moderation channel updated to {mod_c.mention}.")

    @commands.command()
    @commands.has_role('Invigilator')
    async def update_res_channel(self, ctx, res_c: discord.TextChannel):
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp)
            return
        
        self.comp.mod_channel = res_c
        await ctx.send(f"moderation channel updated to {res_c.mention}.")

    @commands.command()
    @commands.has_role('Invigilator')
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

                    await ctx.send("Questions set.")
                except sqlite3.ProgrammingError as e:
                    await ctx.send("Please attach a correctly formatted questions file.")
                    print(e)
            else:
                await ctx.send("Invalid file type.")
        else:
            await ctx.send("Please attach a valid `.csv` file.")

    @commands.command()
    @commands.has_role('Invigilator')
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
                except sqlite3.ProgrammingError as e:
                    await ctx.send("Please attach a correctly formatted teams file.")
                    print(e)
            else:
                await ctx.send("Invalid file type.")
        else:
            await ctx.send("Please attach a valid `.csv` file.")

    @commands.command()
    @commands.has_role('Invigilator')
    async def end_comp(self, ctx):
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp)  # Send a response if you want to notify user
            return
        if self.comp.active:
            await ctx.send("Competition is still active. Use `!stop_comp` to stop competition.")
            return
        
        await ctx.send("Type 'end' to terminate and archive the current competition.")

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
    @commands.has_role('Invigilator')
    async def competitor(self, ctx, tid):
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp) 
            return
        
        self.comp.competitor[ctx.channel.id] = int(tid)
        await ctx.send("Competitor channel added")
        return
    
    @commands.command()
    @commands.has_role('Invigilator')
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
    
    @commands.Cog.listener()
    async def on_message(self, message):
        await self.relayer.on_message(message)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRole):
            await ctx.send('You do not have permission to use this command.')
    
async def setup(bot):
    await bot.add_cog(Competition(bot))