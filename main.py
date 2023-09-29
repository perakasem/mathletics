import os
import discord
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv() # Load variables from .env file

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'logged in as {bot.user}')
    await bot.load_extension("cogs.comp")
    print("competition module loaded")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)