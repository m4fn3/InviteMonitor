import asyncio, discord
from discord.ext import commands

class Help(commands.HelpCommand):
    def __init__(self):
        super().__init__()
        self.description_text = "\nDo you have any questions? Feel free to ask in [official server]({})!"

    async def send_bot_help(self, mapping) -> None:
        cogs: list
        page = 1
        cogs = ["Setting", "Invite", "Manage"]
        embed_org = discord.Embed(title=f"{self.context.bot.user.name} Usage", color=0x00ff00)
        embed_org.description = f"`{self.context.bot.PREFIX}help (command name)` to see detailed description of the command!" + self.description_text.format(self.context.bot.datas['server'])
        for cog_name in cogs:
            cog = discord.utils.get(mapping, qualified_name=cog_name)
            command_list = [command.name for command in await self.filter_commands(cog.get_commands())]
            embed_org.add_field(name=cog_name, value="`"+"`, `".join(command_list)+"`", inline=False)
        message = await self.get_destination().send(embed=embed_org)
        await message.add_reaction("◀️")
        await message.add_reaction("▶️")
        await message.add_reaction("❔")

        def check(r, u):
            return r.message.id == message.id and u == self.context.author and str(r.emoji) in ["◀️", "▶️", "❔"]

        while True:
            try:
                reaction, user = await self.context.bot.wait_for("reaction_add", timeout=60, check=check)
                if str(reaction.emoji) == "▶️":
                    if page == len(cogs) + 1:
                        page = 1
                    else:
                        page += 1
                elif str(reaction.emoji) == "◀️":
                    if page == 1:
                        page = len(cogs) + 1
                    else:
                        page -= 1
                elif str(reaction.emoji) == "❔":
                    embed = discord.Embed(title="How to read the help", color=0x00ff00)
                    embed.description = f"You can move the page by pressing the reaction below the message" + self.description_text.format(self.context.bot.datas['server'])
                    embed.add_field(name="[argument]", value="__**required**__ argument", inline=False)
                    embed.add_field(name="(argument)", value="__**option**__", inline=False)
                    embed.add_field(name="[A|B]", value="either A or B", inline=False)
                    await message.edit(embed=embed)
                    continue
                if page == 1:
                    await message.edit(embed=embed_org)
                    continue
                cog = discord.utils.get(mapping, qualified_name=cogs[page - 2])
                cmds = cog.get_commands()
                embed = discord.Embed(title=cog.qualified_name, color=0x00ff00)
                embed.description = cog.description + self.description_text.format(self.context.bot.datas['server'])
                for cmd in await self.filter_commands(cmds):
                    description = cmd.brief if cmd.brief is not None else cmd.description
                    embed.add_field(name=f"{self.context.bot.PREFIX}{cmd.usage}", value=f"```{description}```", inline=False)
                await message.edit(embed=embed)
            except asyncio.TimeoutError:
                await message.remove_reaction("◀️", self.context.bot.user)
                await message.remove_reaction("▶️", self.context.bot.user)
                await message.remove_reaction("❔", self.context.bot.user)
                break

    async def send_cog_help(self, cog) -> None:
        cmds = cog.get_commands()
        embed = discord.Embed(title=cog.qualified_name, color=0x00ff00)
        embed.description = cog.description
        for cmd in await self.filter_commands(cmds):
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
        for cmd in await self.filter_commands(cmds):
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
