from discord.ext import commands
import discord, traceback2, re
from main import InvStat


class Manage(commands.Cog):
    """__Manage members__"""

    def __init__(self, bot):
        self.bot = bot  # type: InvStat

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f":hourglass_flowing_sand: Interval too fast!\nYou can use this command again __**after {error.retry_after:.2f} sec!**__")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(":placard: Missing required arguments!")
        else:
            await ctx.send(f":tools: Unexpected error has occurred. please contact to bot developer.\n```py{error[:1900]}```")

    @commands.command(usage="kick [@user]", description="Kick the mentioned user and delete invites made by mentioned user")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def kick(self, ctx):
        # 権限を確認
        if not ctx.guild.me.guild_permissions.kick_members:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(":no_entry_sign: Missing required permission **__kick_members__**!\nPlease make sure that BOT has right access.")
        if not ctx.author.guild_permissions.kick_members:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(":no_pedestrians: You don't have **__kick_members__** permisson!\nFor security reasons, this command can only be used by person who have permission.")
        if not ctx.message.mentions:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(":warning: Please mention at least one user!")
        target_users = set()
        for target in ctx.message.mentions:
            try:
                await ctx.guild.get_member(target.id).kick()
            except:
                await ctx.send(f":x: Failed to kick user <@{target.id}>")
            else:
                target_users.add(str(target.id))
        if not target_users:
            return
        for invite in await ctx.guild.invites():
            if str(invite.inviter.id) in target_users:
                await invite.delete()
        mentions_text = "<@" + "> <@".join(target_users) + ">"
        await ctx.send(f":magic_wand: {mentions_text[:1900].rsplit('<', 1)[0] + '...' if len(mentions_text) >= 1900 else mentions_text} has kicked successfully!")

    @commands.command(usage="ban [@user]", description="Ban the mentioned user and delete invites made by mentioned user")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def ban(self, ctx):
        # 権限を確認
        if not ctx.guild.me.guild_permissions.kick_members:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(":no_entry_sign: Missing required permission **__kick_members__**!\nPlease make sure that BOT has right access.")
        if not ctx.author.guild_permissions.kick_members:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(":no_pedestrians: You don't have **__kick_members__** permisson!\nFor security reasons, this command can only be used by person who have permission.")
        if not ctx.message.mentions:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(":warning: Please mention at least one user!")
        target_users = set()
        for target in ctx.message.mentions:
            try:
                await ctx.guild.get_member(target.id).ban()
            except:
                await ctx.send(f":x: Failed to ban user <@{target.id}>")
            else:
                target_users.add(str(target.id))
        if not target_users:
            return
        for invite in await ctx.guild.invites():
            if str(invite.inviter.id) in target_users:
                await invite.delete()
        mentions_text = "<@" + "> <@".join(target_users) + ">"
        await ctx.send(f":magic_wand: {mentions_text[:1900].rsplit('<', 1)[0] + '...' if len(mentions_text) >= 1900 else mentions_text} has banned successfully!")

    @commands.command(usage="kick_with [@user | invite code]", description="Kick the users who invited with mentioned user or specified invite code. Also delete invites made by them.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def kick_with(self, ctx):
        # そのサーバーでログが設定されているか確認
        if self.bot.db[str(ctx.guild.id)]["channel"] is None:
            return await ctx.send(f":warning: Log channel haven't set yet. Please setup by `{self.bot.PREFIX}enable` command before checking status.")
        # 権限を確認
        if not ctx.guild.me.guild_permissions.kick_members:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(":no_entry_sign: Missing required permission **__kick_members__**!\nPlease make sure that BOT has right access.")
        if not ctx.author.guild_permissions.kick_members:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(":no_pedestrians: You don't have **__kick_members__** permisson!\nFor security reasons, this command can only be used by person who have permission.")
        if len(ctx.message.content.split()) == 1:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(":warning: Please specify at least one user or invite code!")
        mentions = {user.id for user in ctx.message.mentions}
        clean_text = re.sub(r"(https?://)?(www.)?(discord.gg|(ptb.|canary.)?discord(app)?.com/invite)/", " ", ctx.message.content.split(" ", 1)[1])
        clean_text = re.sub(r"<@!?\d+>", " ", clean_text)
        invites = set(clean_text.split())
        target_users = set()
        error_msg = ""
        # 招待コードが有効であることを確認する,有効あらばリンクの作成者を対象者に追加
        target_invites = set()
        for invite in invites:
            if invite not in self.bot.cache[str(ctx.guild.id)]:
                error_msg += f":x: `{invite}` is invalid invite code.\n"
            else:
                target_invites.add(invite)
                target_users.add(self.bot.cache[str(ctx.guild.id)][invite]["author"])
        # 指定されたユーザーに招待された人のIDのリストを作成
        for user in self.bot.db[str(ctx.guild.id)]["users"]:
            # 招待者がメンションリストに含まれるか、招待コードが招待コードリストに含まれる場合
            if (self.bot.db[str(ctx.guild.id)]["users"][user]["from"] in mentions) or (self.bot.db[str(ctx.guild.id)]["users"][user]["code"] in target_invites):
                target_users.add(int(user))
        target_users = target_users.union(mentions)
        # Kickに成功した人のみのリストを作成
        target_checked = set()
        for target in target_users:
            try:
                await ctx.guild.get_member(target).kick()
            except:
                error_msg += f":x: Failed to kick user <@{target}>\n"
            else:
                target_checked.add(str(target))
        if error_msg != "":
            await ctx.send(error_msg[:1900].rsplit("\n", 1)[0] + "\n..." if len(error_msg) >= 1900 else error_msg)
        if not target_checked:
            return await ctx.send(":mag: No user found.")
        for invite in await ctx.guild.invites():
            if (str(invite.inviter.id) in target_checked) or (invite.code in invites):
                await invite.delete()
        mentions_text = "<@" + "> <@".join(target_checked) + ">"
        await ctx.send(f":magic_wand: {mentions_text[:1900].rsplit('<', 1)[0] + '...' if len(mentions_text) >= 1900 else mentions_text} has kicked successfully!")

    @commands.command(usage="ban_with [@user | code]", description="Ban the users who invited with mentioned user or specified invite code. Also delete invites made by them.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def ban_with(self, ctx):
        # そのサーバーでログが設定されているか確認
        if self.bot.db[str(ctx.guild.id)]["channel"] is None:
            return await ctx.send(f":warning: Log channel haven't set yet. Please setup by `{self.bot.PREFIX}enable` command before checking status.")
        # 権限を確認
        if not ctx.guild.me.guild_permissions.ban_members:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(":no_entry_sign: Missing required permission **__ban_members__**!\nPlease make sure that BOT has right access.")
        if not ctx.author.guild_permissions.ban_members:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(":no_pedestrians: You don't have **__ban_members__** permisson!\nFor security reasons, this command can only be used by person who have permission.")
        if len(ctx.message.content.split()) == 1:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(":warning: Please specify at least one user or invite code!")
        mentions = {user.id for user in ctx.message.mentions}
        clean_text = re.sub(r"(https?://)?(www.)?(discord.gg|(ptb.|canary.)?discord(app)?.com/invite)/", " ", ctx.message.content.split(" ", 1)[1])
        clean_text = re.sub(r"<@!?\d+>", " ", clean_text)
        invites = set(clean_text.split())
        target_users = set()
        error_msg = ""
        # 招待コードが有効であることを確認する,有効あらばリンクの作成者を対象者に追加
        target_invites = set()
        for invite in invites:
            if invite not in self.bot.cache[str(ctx.guild.id)]:
                error_msg += f":x: `{invite}` is invalid invite code.\n"
            else:
                target_invites.add(invite)
                target_users.add(self.bot.cache[str(ctx.guild.id)][invite]["author"])
        # 指定されたユーザーに招待された人のIDのリストを作成
        for user in self.bot.db[str(ctx.guild.id)]["users"]:
            # 招待者がメンションリストに含まれるか、招待コードが招待コードリストに含まれる場合
            if (self.bot.db[str(ctx.guild.id)]["users"][user]["from"] in mentions) or (self.bot.db[str(ctx.guild.id)]["users"][user]["code"] in target_invites):
                target_users.add(int(user))
        target_users = target_users.union(mentions)
        # Kickに成功した人のみのリストを作成
        target_checked = set()
        for target in target_users:
            try:
                await ctx.guild.get_member(target).ban()
            except:
                error_msg += f":x: Failed to ban user <@{target}>\n"
            else:
                target_checked.add(str(target))
        if error_msg != "":
            await ctx.send(error_msg[:1900].rsplit("\n", 1)[0] + "\n..." if len(error_msg) >= 1900 else error_msg)
        if not target_checked:
            return await ctx.send(":mag: No user found.")
        for invite in await ctx.guild.invites():
            if (str(invite.inviter.id) in target_checked) or (invite.code in invites):
                await invite.delete()
        mentions_text = "<@" + "> <@".join(target_checked) + ">"
        await ctx.send(f":magic_wand: {mentions_text[:1900].rsplit('<', 1)[0] + '...' if len(mentions_text) >= 1900 else mentions_text} has banned successfully!")


def setup(bot):
    bot.add_cog(Manage(bot))
