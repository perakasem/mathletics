"""
Main module for the Mathletics Steward Discord bot.

Environment Variables:
    DISCORD_TOKEN (str): Used to authenticate the bot with Discord's API.

Dependencies:
    discord.py: Uused to interact with Discord's API.
    python-dotenv: For loading environment variables from the .env file.

Extensions:
    comp: The main competition module.

Usage:
    Run this script to start the bot. Ensure that a valid DISCORD_TOKEN is set in your environment or .env file.
"""

import os
import discord
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv() # Load variables from .env file

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Initialize intents permissions, and bot instance
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Load extensions
@bot.event
async def on_ready():
    print(f'logged in as {bot.user}')
    await bot.load_extension("comp")
    print("competition module loaded")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)