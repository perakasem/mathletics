import discord
from discord.ext import commands

bot = commands.Bot(command_prefix=";")

@bot.slash_command(name="first_slash", guild_ids=[...])
async def first_slash(ctx): 
    await ctx.respond("You executed the slash command!")

@bot.event
async def on_ready():
    print("the bot is ready!")

bot.run("MTEwODYzMjcwMzc0Nzc2MDE1OA.GTapxI.h16G67DlxQ0ZtJQk4CUa6HW8VfwTKvKQqdRUQQ")