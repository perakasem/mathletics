"""
Module to handle message relaying in Discord.

Classes:
    ReactionRelayer: Manages the relaying of messages between channels in a Discord server upon the addition of specific reactions.
    Relayer: Manages the relaying of messages between channels in a Discord server once enabled.

Dependencies:
    discord.py: Python library for interacting with the Discord API.

Example:
    To use the ReactionRelayer class, import it into your bot's file:
    
    ```python
    from relayer import *
    ```

Note:
    This module requires the discord.ext.commands framework for proper integration into a Discord bot.
"""

import discord

class ReactionRelayer:
    """
    Provides togglable relaying between channels on reaction add. 

    Attributes:
        CHECK_MARK_EMOJI (str): A constant containing the reaction to be used for relaying.
        bot (discord.ext.commands.Bot): Current instance of the Discord bot.
        enabled_channels (set): A set of channel IDs where the relay feature is enabled.
        relay_channels (dict): A dictionary mapping source channel IDs to their corresponding destination channel IDs. 
    """
    def __init__(self, bot) -> None:
        self.CHECK_MARK_EMOJI = '✅'
        self.bot = bot
        self.enabled_channels = set()
        self.relay_channels = {}

    async def on_message(self, message) -> None:
        """Listens for messages in channels and adds a reaction to messages in enabled channels.

        Args:
            message: The message object that triggers the event.
        """
        if message.author == self.bot.user:
            return # Prevent the bot from reacting to its own messages

        # Check if the message is in an enabled source channel
        if message.channel.id in self.enabled_channels:
            await message.add_reaction(self.CHECK_MARK_EMOJI)

        await self.bot.process_commands(message)

    async def on_reaction_add(self, reaction, user) -> None:
        """Handles added reactions and relays messages if conditions are met.

        Args:
            reaction: The reaction object added to the message.
            user: The user who added the reaction.
        """
        if user == self.bot.user:
            return # Avoid processing reactions made by the bot

        if reaction.emoji == self.CHECK_MARK_EMOJI and reaction.message.channel.id in self.enabled_channels:
            source_channel = reaction.message.channel
            relay_channel = self.bot.get_channel(self.relay_channels.get(source_channel.id))
            
            if relay_channel:
                author_name = reaction.message.author.name
                content = f"{author_name}: {reaction.message.content}"

                await relay_channel.send(content)

    async def enable_reaction_relay(self, ctx, destination_channel: discord.TextChannel) -> None:
        """Enables reaction relay from the current channel to a specified destination channel.

        Args:
            ctx: The context in which the command is invoked.
            destination_channel (discord.TextChannel): The destination channel for relayed messages.
        """
        self.enabled_channels.add(ctx.channel.id)
        source_channel_id = ctx.channel.id
        self.relay_channels[source_channel_id] = destination_channel.id
        await ctx.send(f"Relaying enabled! Messages from this channel will be relayed to {destination_channel.mention}.")

    async def disable__reaction_relay(self, ctx) -> None:
        """Disables the reaction relay in the current channel.

        Args:
            ctx: The context in which the command is invoked.
        """
        self.enabled_channels.discard(ctx.channel.id)
        await ctx.send(f"Relay disabled in this channel: {ctx.channel.name}")

class Relayer:
    """Relays messages from a source channel to a destination channel.

    Attributes:
        bot (discord.ext.commands.Bot): Current instance of the Discord bot.
        enabled_channels (set): A set of channel IDs where the relay feature is enabled.
        relay_channels (dict): A dictionary mapping source channel IDs to their corresponding destination channel IDs. 
    """
    def __init__(self, bot) -> None:
        self.bot = bot
        self.enabled_channels = set()
        self.relay_channels = {}

    async def on_message(self, message) -> None:
        """Listens for messages in channels and relays the message to enabled channels.

        Args:
            message: The message object that triggers the event.
        """
        if message.author == self.bot.user:
            return  # Avoid processing messages made by the bot

        if message.channel.id in self.enabled_channels:
            source_channel = message.channel
            relay_channel = self.bot.get_channel(self.relay_channels.get(source_channel.id))
            
            if relay_channel:
                author_name = message.author.name
                await relay_channel.send(f"{author_name}: {message.content}")

    async def enable_relay(self, source_channel_id: int, destination_channel: discord.TextChannel) -> None:
        """
        Enables the relaying of messages from the current channel to the specified destination channel.

        Args:
            source_channel_id (int): The Discord text channel id of the source channel.
            destination_channel (discord.TextChannel): The destination channel object.

        """
        source_channel = self.bot.get_channel(source_channel_id)
        self.enabled_channels.add(source_channel_id)
        self.relay_channels[source_channel_id] = destination_channel.id
        await source_channel.send(f"Relaying enabled. Destination: {destination_channel.mention}.")

    async def disable_relay(self, source_channel_id: int) -> None:
        """Disables message relaying in active channels.

        Args:
            source_channel_id (int): The Discord text channel id of the source channel.
        """
        source_channel = self.bot.get_channel(source_channel_id)
        self.enabled_channels.discard(source_channel_id)
        await source_channel.send("Relay disabled.")