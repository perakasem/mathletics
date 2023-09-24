import discord
from os import getenv
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()  # Load variables from .env file

DISCORD_TOKEN = getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

CHECK_MARK_EMOJI = '✅'
enabled_channels = set()  # Set of channels where the relay feature is enabled
relay_channels = {}  # Dictionary of source channel IDs to destination channel IDs

@bot.event
async def on_ready():
    print(f'loggded in as {bot.user}')

@bot.event
async def on_message(message):
    # Prevent the bot from reacting to its own messages
    if message.author == bot.user:
        return

    # Check if the message is in a channel where you want this feature
    if message.channel.id in enabled_channels:
        await message.add_reaction(CHECK_MARK_EMOJI)

    # Process commands (important if you're using the on_message event and commands)
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:
        return  # Avoid processing reactions made by the bot

    if reaction.emoji == CHECK_MARK_EMOJI and reaction.message.channel.id in enabled_channels:
        source_channel = reaction.message.channel
        relay_channel = bot.get_channel(relay_channels.get(source_channel.id))
        
        if relay_channel:
            author_name = reaction.message.author.name
            content = f"{author_name}: {reaction.message.content}"

            await relay_channel.send(content)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def enable_relay(ctx, destination_channel: discord.TextChannel):
    enabled_channels.add(ctx.channel.id)
    """Enable relaying of messages from the current channel to the specified destination channel."""
    source_channel_id = ctx.channel.id
    relay_channels[source_channel_id] = destination_channel.id
    await ctx.send(f"Relaying enabled! Messages from this channel will be relayed to {destination_channel.mention}.")

@bot.command()
# @commands.has_permissions(manage_channels=True)  # Only members with the 'manage_channels' permission can use this command
async def disable_relay(ctx):
    enabled_channels.discard(ctx.channel.id)
    await ctx.send(f"Relay disabled in this channel: {ctx.channel.name}")

bot.run(DISCORD_TOKEN)
