import asyncio
import discord

from discord.ext import commands
import identifier

class Help(commands.HelpCommand):
    def __init__(self):
        super().__init__()
        self.description_text = "\n[Need help? Visit the support server!]({})"
        self.footer_text = "{}help [command]  to learn more!"

    async def send_bot_help(self, mapping) -> None:
        cogs: list
        page = 1
        cogs = ["Setting", "Invite", "Manage", "Cache"]
        # 一枚目の全コマンドリストEmbedを作成
        embed_org = discord.Embed(title=f"{self.context.bot.user.name} Usage", color=0x00ff00)
        embed_org.description = self.footer_text.format(self.context.bot.PREFIX) + self.description_text.format(self.context.bot.static_data.server)
        for cog_name in cogs:
            cog = discord.utils.get(mapping, qualified_name=cog_name)
            command_list = [command.name for command in identifier.filter_hidden_commands(cog.get_commands())]
            embed_org.add_field(name=cog_name, value="`" + "`, `".join(command_list) + "`", inline=False)
        message = await self.get_destination().send(embed=embed_org)
        await message.add_reaction("◀️")
        await message.add_reaction("▶️")
        await message.add_reaction("❔")

        def check(r, u):
            return r.message.id == message.id and u == self.context.author and str(r.emoji) in ["◀️", "▶️", "❔"]

        while True:
            try:
                reaction, user = await self.context.bot.wait_for("reaction_add", timeout=60, check=check)
                if str(reaction.emoji) == "▶️":  # 次のページに進む
                    if page == len(cogs) + 1:
                        page = 1
                    else:
                        page += 1
                elif str(reaction.emoji) == "◀️":  # 前のページに戻る
                    if page == 1:
                        page = len(cogs) + 1
                    else:
                        page -= 1
                elif str(reaction.emoji) == "❔":  # 記号説明ページ
                    embed = discord.Embed(title="How to read the help", color=0x00ff00)
                    embed.description = f"You can move the page by pressing the reaction below the message" + self.description_text.format(self.context.bot.static_data.server)
                    embed.add_field(name="[argument]", value="→ __**required**__ argument", inline=False)
                    embed.add_field(name="(argument)", value="→ __**optional**__ argument", inline=False)
                    embed.add_field(name="[A|B]", value="→ either A or B", inline=False)
                    embed.add_field(name="Others", value="code ... Invite Code")
                    await message.edit(embed=embed)
                    continue
                if page == 1:  # 既に用意された1枚目を表示
                    await message.edit(embed=embed_org)
                    continue
                cog = discord.utils.get(mapping, qualified_name=cogs[page - 2])
                embed = discord.Embed(title=cog.qualified_name, color=0x00ff00)
                desc = cog.description + self.description_text.format(self.context.bot.static_data.server) + "\n"
                command_list = cog.get_commands()
                max_length = self.get_command_max_length(command_list)
                for cmd in identifier.filter_hidden_commands(command_list):
                    # 適切な空白数分、空白を追加 -> `i/enable  |` 有効にします
                    desc += f"\n`i/{cmd.name}" + " " * self.get_space_count(len(cmd.name), max_length) + f"|` {cmd.brief}"
                embed.description = desc
                embed.set_footer(text=self.footer_text.format(self.context.bot.PREFIX))
                await message.edit(embed=embed)
            except asyncio.TimeoutError:
                await message.remove_reaction("◀️", self.context.bot.user)
                await message.remove_reaction("▶️", self.context.bot.user)
                await message.remove_reaction("❔", self.context.bot.user)
                break

    def get_space_count(self, name: int, max_length: int) -> int:
        diff = max_length - name
        if diff < 0:
            return 0
        else:
            return diff

    def get_command_max_length(self, command_list):
        max_length = 8
        for command in command_list:
            if len(command.name) > max_length:
                max_length = len(command.name)
        return max_length

    async def send_cog_help(self, cog) -> None:
        embed = discord.Embed(title=cog.qualified_name, color=0x00ff00)
        desc = cog.description + self.description_text.format(self.context.bot.static_data.server) + "\n"
        command_list = cog.get_commands()
        max_length = self.get_command_max_length(command_list)
        for cmd in identifier.filter_hidden_commands(command_list):
            # 適切な空白数分、空白を追加 -> `i/enable  |` 有効にします
            desc += f"\n`i/{cmd.name}" + " " * self.get_space_count(len(cmd.name), max_length) + f"|` {cmd.brief}"
        embed.description = desc
        embed.set_footer(text=self.footer_text.format(self.context.bot.PREFIX))
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(title=f"{self.context.bot.PREFIX}{group.usage}", color=0x00ff00)
        embed.description = f"```{group.description}```\n"
        if group.aliases:
            embed.add_field(name="Alias:", value="`" + "`, `".join(group.aliases) + "`", inline=False)
        if group.help:
            embed.add_field(name="Example:", value=group.help.format(self.context.bot.PREFIX), inline=False)
        cmds = group.walk_commands()
        for cmd in identifier.filter_hidden_commands(cmds):
            embed.add_field(name=f"{self.context.bot.PREFIX}{cmd.usage}", value=f"→ {cmd.description}", inline=False)
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
