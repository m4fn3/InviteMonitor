import asyncio, discord
from discord.ext import commands

class Help(commands.HelpCommand):
    def __init__(self):
        super().__init__()
        self.no_category = "Help"

    async def send_bot_help(self, mapping) -> None:
        cogs = ["Invite"]
        embed = discord.Embed(title="InvStat Commands", color=0x00ff00)
        for cog_name in cogs:
            cog = self.context.bot.get_cog(cog_name)


    async def send_cog_help(self, cog) -> None:
        cmds = cog.get_commands()
        embed = discord.Embed(title=cog.qualified_name, color=0x00ff00)
        embed.description = cog.description
        for cmd in await self.filter_commands(cmds, sort=True):
            embed.add_field(name=f"{self.context.bot.PREFIX}{cmd.usage}", value=f"```{cmd.description}```", inline=False)
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(title=f"{self.context.bot.PREFIX}{group.usage}", color=0x00ff00)
        embed.description = f"```{group.description}```"
        if group.aliases:
            embed.add_field(name="Alias:", value="`" + "`, `".join(group.aliases) + "`", inline=False)
        if group.help:
            embed.add_field(name="Example:", value=group.help.format(self.context.bot.PREFIX), inline=False)
        cmds = group.walk_commands()
        embed.add_field(name="Subcommand:", value=f"{sum(1 for _ in await self.filter_commands(group.walk_commands()))}")
        for cmd in await self.filter_commands(cmds, sort=True):
            embed.add_field(name=f"{self.context.bot.PREFIX}{cmd.usage}", value=f"{cmd.description}", inline=False)
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command) -> None:
        embed = discord.Embed(title=f"{self.context.bot.PREFIX}{command.usage}", color=0x00ff00)
        embed.description = f"```{command.description}```"
        if command.aliases:
            embed.add_field(name="Alias:", value="`" + "`, `".join(command.aliases) + "`", inline=False)
        if command.help:
            embed.add_field(name="Example:", value=command.help.format(self.context.bot.PREFIX), inline=False)
        await self.get_destination().send(embed=embed)

    async def send_error_message(self, error) -> None:
        embed = discord.Embed(title="Help Error", description=error, color=0xff0000)
        await self.get_destination().send(embed=embed)

    def command_not_found(self, string):
        return f"Command **{string}** was not found!\nPlease check the command name!"

    def subcommand_not_found(self, cmd, string):
        if isinstance(cmd, commands.Group) and len(cmd.all_commands) > 0:
            return f"Subcommand **{string}** is not registered to **{cmd.qualified_name}** command!\nPlease check correct usage by __**{self.context.bot.PREFIX}help {cmd.qualified_name}**__"
        return f"**{cmd.qualified_name}** command doesn't have subcommand!\nPlease check correct usage by __**{self.context.bot.PREFIX}help {cmd.qualified_name}**__"
E