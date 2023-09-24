import discord
from discord.ext import commands

class Relayer:

    def __init__(self, bot):
        self.CHECK_MARK_EMOJI = '✅'
        self.bot = bot
        self.enabled_channels = set()  # Set of channels where the relay feature is enabled
        self.relay_channels = {}  # Dictionary of source channel IDs to destination channel IDs
        

    @commands.Cog.listener()
    async def on_message(self, message):
        # Prevent the bot from reacting to its own messages
        if message.author == self.bot.user:
            return

        # Check if the message is in a channel where you want this feature
        if message.channel.id in self.enabled_channels:
            await message.add_reaction(self.CHECK_MARK_EMOJI)

        # Process commands (important if you're using the on_message event and commands)
        await self.bot.process_commands(message)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user == self.bot.user:
            return  # Avoid processing reactions made by the bot

        if reaction.emoji == self.CHECK_MARK_EMOJI and reaction.message.channel.id in self.enabled_channels:
            source_channel = reaction.message.channel
            relay_channel = self.bot.get_channel(self.relay_channels.get(source_channel.id))
            
            if relay_channel:
                author_name = reaction.message.author.name
                content = f"{author_name}: {reaction.message.content}"

                await relay_channel.send(content)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def enable_relay(self, ctx, destination_channel: discord.TextChannel):
        self.enabled_channels.add(ctx.channel.id)
        """Enable relaying of messages from the current channel to the specified destination channel."""
        source_channel_id = ctx.channel.id
        self.relay_channels[source_channel_id] = destination_channel.id
        await ctx.send(f"Relaying enabled! Messages from this channel will be relayed to {destination_channel.mention}.")

    @commands.command()
    # @commands.has_permissions(manage_channels=True)  # Only members with the 'manage_channels' permission can use this command
    async def disable_relay(self, ctx):
        self.enabled_channels.discard(ctx.channel.id)
        await ctx.send(f"Relay disabled in this channel: {ctx.channel.name}")