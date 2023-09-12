import discord
import os
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()  # Load variables from .env file

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents(messages=True, message_content=True, reactions=True)

bot = commands.Bot(command_prefix="!", intents=intents)

RELAY_CHANNEL_ID = 1138806960129581066 # ID of the channel where you want to relay the message to
CHECK_MARK_EMOJI = '✅'
enabled_channels = set()  # Set of channels where the relay feature is enabled

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:
        return  # Avoid processing reactions made by the bot

    if str(reaction.emoji) == CHECK_MARK_EMOJI and reaction.message.channel.id in enabled_channels:
        source_channel = reaction.message.channel
        relay_channel = bot.get_channel(RELAY_CHANNEL_ID)

        if relay_channel:
            embed = discord.Embed(
                description=reaction.message.content,
                color=0x00ff00,
                timestamp=reaction.message.created_at
            )
            embed.set_author(name=reaction.message.author.name, icon_url=reaction.message.author.avatar_url)
            embed.set_footer(text=f"Relayed from #{source_channel.name}")

            await relay_channel.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_channels=True)  # Only members with the 'manage_channels' permission can use this command
async def enable_relay(ctx):
    enabled_channels.add(ctx.channel.id)
    await ctx.send(f"Relay enabled in this channel: {ctx.channel.name}")

@bot.command()
@commands.has_permissions(manage_channels=True)  # Only members with the 'manage_channels' permission can use this command
async def disable_relay(ctx):
    enabled_channels.discard(ctx.channel.id)
    await ctx.send(f"Relay disabled in this channel: {ctx.channel.name}")

bot.run(DISCORD_TOKEN)
