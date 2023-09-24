import os, discord
from dotenv import load_dotenv
from discord.ext import commands
from comp import Competition

load_dotenv() # Load variables from .env file

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'loggded in as {bot.user}')

bot.add_cog(Competition(bot))

bot.run(DISCORD_TOKEN)