import discord
from discord.ext import commands

class Help(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        channel = self.get_destination()
        embed = discord.Embed(title='Help', description='List of available commands:', color=discord.Color.blue())
        
        for cog, commands in mapping.items():
            # Skip hidden commands and empty cogs
            visible_commands = [command for command in commands if not command.hidden]
            if len(visible_commands) == 0:
                continue

            command_signatures = [self.get_command_signature(command) for command in visible_commands]
            embed.add_field(name=f'{cog.qualified_name}' if cog else 'No Category', value='\n'.join(command_signatures), inline=False)

        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))