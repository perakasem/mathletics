"""
Module to handle all competition related commands for configuration, moderation, and participation.

This module contains the ReactionRelayer class, which provides functionality for a Discord bot to relay messages between channels based on reaction emojis. It is designed to be used as a cog within a Discord bot using the discord.ext.commands framework. The module facilitates the toggling of message relay based on specific reactions (like a check mark) in designated channels.

Classes:
    Comp: Stores ongoing competition data as an entity for competition tracking.
    Competition: Manages the entire competition.

Dependencies:
    os: Provides a way to interact with the operating system, particularly for environment variable access and path operations.
    csv: Implements classes to read and write tabular data in CSV format.
    asyncio: Enables asynchronous programming, used for managing asynchronous tasks and coroutines.
    sqlite3: A built-in library for interacting with SQLite databases.
    discord: The core library for Discord bot development, enabling bot functionalities.
    relayer: A custom module for message relaying functionalities in Discord.
    db_init: A custom module for initializing the database.
    typing: Provides support for type hints, enhancing code readability and type checking.
    os.path: Submodule of 'os' for manipulating file system paths.
    datetime: Provides classes for manipulating dates and times.
    discord.ext.commands: Extension of the discord.py library, simplifies command parsing and handling.
    graph: A custom module for generating live leaderboard graphs
    scoring: A custom module for calculating scores.

Example:
    To use the Comp class, load this cog as an extension:
    
    ```python
    @bot.event
    async def on_ready():
        await bot.load_extension("comp")
    ```

Note:
    This module requires the discord.ext.commands framework for proper integration into a Discord bot.
"""

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
    """
    Stores ongoing competition data as an entity for competition tracking.

    Attributes:
        comp_name (str): The name of the competition.
        mod_channel (discord.TextChannel): The Discord channel designated for moderation.
        res_channel (discord.TextChannel): The Discord channel where results are posted.
        active (bool): Indicates whether the competition is currently active. Default is False.
        db_path (str): Path to the database file for the competition.
        plots_path (str): Path to temporary live leaderboard files.
        competitor (dict): Tracks competitor channels.
        submitting_channels (set): Channels allowed to submit competition entries.

    Args:
        name (str): The name of the competition.
        mod (discord.TextChannel): The Discord channel for moderation.
        res (discord.TextChannel): The Discord channel for posting results.
        path (str): File path to the competitions database.
    """
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
    """
    Contains all competition methods and commands.

    Attributes:
        bot (discord.ext.commands.Bot): Current instance of the Discord bot.
        relayer (Relayer): Message relayer for current bot instance. 
        comp (Comp): Comp class instance. Default is none. 

    Args:
        bot (discord.ext.commands.Bot): Current instance of the Discord bot.
    """
    def __init__(self, bot):
        self.bot = bot
        self.relayer = Relayer(bot)
        self.comp = None

    @commands.command()
    async def hello(self, ctx):
        """Sends a basic greeting and instructions for further assistance in the Discord channel.

        Args:
            ctx (commands.Context): The context in which the command is called. 

        Returns:
            None.
        """
        await ctx.send("Hello! I am Mathletics Steward. Use `!help` to access commands, or contact the administrator to learn more.")

    @commands.command()
    @commands.has_role('Invigilator')
    async def status(self, ctx) -> None:
        """Indicates competition status and outlines assigned channels.

        Args:
            ctx (commands.Context): The context (channel) in which the command is called. 

        Sends:
            message: Error message.
            embed: Competition name, moderation channel, results channel, status, competitor channels.

        Note:
            Only sends status when a competition is active.
        """
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
    async def set_comp(self, ctx, comp_name=None, mod_c: Optional[discord.TextChannel] = None, res_c: Optional[discord.TextChannel] = None) -> None:
        """Indicates competition status and outlines assigned channels.

        Args:
            ctx (commands.Context): The context (channel) in which the command is called. 
            comp_name (str): The name of the competition. Default is None.
            mod_c (discord.TextChannel): Competition moderation channel object. Default is None.
            res_c (discord.TextChannel): Live results channel object. Default is None.

        Sends:
            message: Argument handling error messages.
            message: Confirmation messages.

        Note:
            Only sets comp when arguments are valid.
        """
        # Argument validity checking
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
        
        # instantiate competition class and create competition database
        self.comp = Comp(comp_name, mod_c, res_c, path)
        create_db(comp_name)

        await ctx.send(f"Competition {comp_name} created! Moderation will be done in {mod_c.mention} and results will be posted in {res_c.mention}.")
        await ctx.send("Please use `!set_questions <csv>` to add questions and `!set_teams <csv>` to add teams to the competition.")
    
    @commands.command()
    @commands.has_role('Invigilator')
    async def start_comp(self, ctx) -> None:
        """Starts competition: enables message relaying and displays empty leaderboard.

        Args:
            ctx (commands.Context): The context (channel) in which the command is called.

        Sends:
            message: Status error messages.
            message: Confirmation messages.
            image: Empty leaderboard.

        Note:
            Only starts comp if comp is inactive and is set.
        """
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
    async def stop_comp(self, ctx) -> None:
        """Stops competition: disables message relaying and notifies all competitors.

        Args:
            ctx (commands.Context): The context (channel) in which the command is called.

        Sends:
            message: Status error messages.
            message: Confirmation messages.

        Note:
            Only stops comp if comp is active and is set.
        """
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
    async def submit(self, ctx, question) -> None:
        """Prompts question confirmation, prompts answer input, calculates score, sends updates to submitter, updates live leaderboard.

        Args:
            ctx (commands.Context): The context (channel) in which the command is called.
            question (int): Question number to be submitted.

        Sends:
            message: Status error messages.
            message: Input prompts.
            message: Confirmation messages.
            embed: Post-submission competitor status updates.

        Raises:
            sqlite3.OperationalError: Errors in querying or updating the competition database.
        
        Note:
            Only available when competition is set and is active, and another question is not active in the same channel.
        """
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send("Competition has not started.") 
            return

        if not self.comp.active:
            await ctx.send("Competition has not started.")
            return
        
        if ctx.channel.id in self.comp.submitting_channels:
            await ctx.send("The command is currently running in this channel! Please wait.")
            return
        
        # Prompt while competition has not stopped.
        while self.comp.active:
            correct = False
            attempts = 0

            tid = self.comp.competitor.get(ctx.channel.id) # Team ID
            time = 0

            conn = sqlite3.connect(self.comp.db_path)
            c = conn.cursor()
                     
            try:
                base_score = c.execute("SELECT base_score FROM questions WHERE id = ?", (question,)).fetchone()[0]
                print(f"got base score: {base_score}")
            except Exception:
                print("error in querying base score")
            
            # check for question existence
            try:
                question_check = c.execute("SELECT * FROM questions WHERE id = ?", (question,)).fetchone()
                print("found question row")
            except Exception:
                print("error in checking question's existence")

            if question_check is None:
                print("question not found")
                await ctx.send("**Chosen question does not exist!**")
                return

            # Send pre-confirmation question details
            embed = discord.Embed(title="Question Overview", description=f"Question: {question}", color=0xb8eefa)
            embed.add_field(name="Maximum Achievable Score", value=f"{base_score}", inline=True)
            await ctx.send(embed=embed)

            await ctx.send(f"Enter the question number to start question {question} or any character to cancel:")

            # Check for authenticity of submission
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

                    embed = discord.Embed(title="Submission Results", description=f"Question: {question}", color=0x00ff00) # 0x00ff00 is a green color for "correct"
                    embed.add_field(name="Result", value="Correct", inline=True)
                    embed.add_field(name="Attempts", value=f"{attempts}", inline=True)
                    embed.add_field(name="Time", value=f"{time}", inline=True)
                    await ctx.send(embed=embed)

                    mod_embed = discord.Embed(title=f"Team {tid}", description=f"Question {question} Submission Results", color=0x00ff00) # Green for "correct"
                    mod_embed.add_field(name="Result", value="Correct", inline=True)
                    mod_embed.add_field(name="Attempts", value=f"{attempts}", inline=True)
                    mod_embed.add_field(name="Time", value=f"{time}", inline=True)
                    await self.comp.mod_channel.send(embed=mod_embed)

                else:
                    time = (datetime.now() - start_time).seconds

                    embed = discord.Embed(title="Submission Results", description=f"Question: {question}", color=0xff0000) # 0xff0000 is red for "incorrect"
                    embed.add_field(name="Result", value="Incorrect", inline=True)
                    embed.add_field(name="Attempts", value=str(attempts), inline=True)
                    embed.add_field(name="Elapsed Time", value=f"{time} seconds", inline=True)
                    await ctx.send(embed=embed)

                    mod_embed = discord.Embed(title=f"Team {tid}", description=f"Question {question} Submission Results", color=0xff0000) # 0xff0000 is red, representing "incorrect"
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
            
            # calculate scores
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
    async def update_mod_channel(self, ctx, mod_c: discord.TextChannel) -> None:
        """Updates moderation channel to current channel.

        Args:
            ctx (commands.Context): The context (channel) in which the command is called.
            mod_c (discord.TextChannel): Competition moderation channel object. 

        Sends:
            message: Status error message.
            message: Confirmation message.
        
        Note:
            Only available when competition is set.
        """
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp)
            return
        
        self.comp.mod_channel = mod_c
        await ctx.send(f"moderation channel updated to {mod_c.mention}.")

    @commands.command()
    @commands.has_role('Invigilator')
    async def update_res_channel(self, ctx, res_c: discord.TextChannel) -> None:
        """Updates moderation channel to current channel.

        Args:
            ctx (commands.Context): The context (channel) in which the command is called.
            res_c (discord.TextChannel): Live results channel object. Default is None.

        Sends:
            message: Status error message.
            message: Confirmation message.
        
        Note:
            Only available when competition is set.
        """
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp)
            return
        
        self.comp.mod_channel = res_c
        await ctx.send(f"moderation channel updated to {res_c.mention}.")

    @commands.command()
    @commands.has_role('Invigilator')
    async def set_questions(self, ctx) -> None:
        """Populates the competition database with uploaded questions and answers in CSV format per the following structure.
        
        | Question No. | Answer | Base Score |
        |--------------|--------|------------|

        Args:
            ctx (commands.Context): The context (channel) in which the command is called.

        Sends:
            message: Status error message.
            message: Confirmation message.
        
        Raises: 
            sqlite3.ProgrammingError: CSV file not attached.
        
        Note:
            Only available when competition is set.
        """
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
    async def set_teams(self, ctx) -> None:
        """Populates the teams database with uploaded teams data in CSV format per the following structure.
        
        | Team ID | Team Name | Members | Completed QIDs | Score |
        |---------|-----------|---------|----------------|-------|

        Args:
            ctx (commands.Context): The context (channel) in which the command is called.

        Sends:
            message: Status error message.
            message: Confirmation message.
        
        Raises: 
            sqlite3.ProgrammingError: CSV file not attached.
        
        Note:
            Only available when competition is set.
        """
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
    async def end_comp(self, ctx) -> None:
        """Terminates the current competition and archives the database, following multiple moderator confirmations.

        Args:
            ctx (commands.Context): The context (channel) in which the command is called.

        Sends:
            message: Status error message.
            message: Confirmation message.
        
        Note:
            Only available when competition is set and has been stopped.
        """
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp)
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
    async def competitor(self, ctx, tid) -> None:
        """Initializes channel as the submission space for the specified team.

        Args:
            ctx (commands.Context): The context (channel) in which the command is called.
            tid (int): The team ID corresponding to the competitor channel

        Sends:
            message: Status error message.
            message: Confirmation message.
        
        Note:
            Only available when competition is set.
        """
        if not hasattr(self, 'comp') or self.comp is None:
            await ctx.send(nocomp) 
            return
        
        self.comp.competitor[ctx.channel.id] = int(tid)
        await ctx.send("Competitor channel added")
        return
    
    @commands.command()
    @commands.has_role('Invigilator')
    async def remove_competitor(self, ctx) -> None:
        """Removes channel from active submission channels.

        Args:
            ctx (commands.Context): The context (channel) in which the command is called.

        Sends:
            message: Status error message.
            message: Confirmation message.
        
        Note:
            Only available when competition is set and current channel is a competitor channel.
        """
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
    async def on_message(self, message) -> None:
        """Relays message when relayer is active.

        Args:
            ctx (commands.Context): The context (channel) in which the command is called.
            message: Message to be relayed.

        Sends:
            message: Relays message to the destination channel.
        """
        await self.relayer.on_message(message)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error) -> None:
        """Notifies caller that they lack permission to use certain commands.

        Args:
            ctx (commands.Context): The context (channel) in which the command is called.
            error (Exception): The error raised when the caller lacks permission.

        Sends:
            message: Permission error message.
        """
        if isinstance(error, commands.MissingRole):
            await ctx.send('You do not have permission to use this command.')
    
async def setup(bot) -> None:
    await bot.add_cog(Competition(bot)) # Add Competition class as a cog