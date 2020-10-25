import re

from discord.ext import commands

from main import InviteMonitor
import identifier
from identifier import error_embed_builder, success_embed_builder, warning_embed_builder

class Manage(commands.Cog):
    """Manage members"""

    def __init__(self, bot):
        self.bot = bot  # type: InviteMonitor

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f":hourglass_flowing_sand: Interval too fast!\nYou can use this command again __**after {error.retry_after:.2f} sec!**__")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(":placard: Missing required arguments!")
        elif isinstance(error, commands.CheckFailure):
            pass
        else:
            await ctx.send(f":tools: Unexpected error has occurred. please contact to bot developer.\n```py\n{str(error)[:1900]}```")

    @identifier.is_has_kick_members()
    @commands.command(usage="kick [@user]", brief="Kick and wipe their invite", description="Kick the mentioned user and delete invites made by that user.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def kick(self, ctx):
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

    @identifier.is_has_ban_members()
    @commands.command(usage="ban [@user]", brief="Ban and wipe their invite", description="Ban the mentioned user and delete invites made by that user.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def ban(self, ctx):
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

    @identifier.is_has_kick_members()
    @commands.command(usage="kick_with [@user | invite code]", brief="Kick with inviter or code", description="Kick the members who was invited by specified user or invite code. Also delete invites made by them.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def kick_with(self, ctx):
        # そのサーバーでログが設定されているか確認
        if not await self.bot.db.is_enabled_guild(ctx.guild.id):
            return await ctx.send(f":warning: Monitoring not enabled! Please setup by `{self.bot.PREFIX}enable` command before this feature.")
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
            if invite not in self.bot.cache[ctx.guild.id]:
                error_msg += f":x: `{invite}` is invalid invite code.\n"
            else:
                target_invites.add(invite)
                target_users.add(self.bot.cache[ctx.guild.id][invite]["author"])
        # 指定されたユーザーに招待された人のIDのリストを作成
        for user in await self.bot.db.get_guild_users(ctx.guild.id):
            # 招待者がメンションリストに含まれるか、招待コードが招待コードリストに含まれる場合
            if (await self.bot.db.get_user_invite_from(ctx.guild.id, user) in mentions) or (await self.bot.db.get_user_invite_code(ctx.guild.id, user) in target_invites):
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
            return await ctx.send(f"{self.bot.static_data.emoji.no_mag} No user found.")
        for invite in await ctx.guild.invites():
            if (str(invite.inviter.id) in target_checked) or (invite.code in invites):
                await invite.delete()
        mentions_text = "<@" + "> <@".join(target_checked) + ">"
        await ctx.send(f":magic_wand: {mentions_text[:1900].rsplit('<', 1)[0] + '...' if len(mentions_text) >= 1900 else mentions_text} has kicked successfully!")

    @identifier.is_has_ban_members()
    @commands.command(usage="ban_with [@user | code]", brief="Ban with inviter or code", description="Ban the members who was invited by specified user or invite code. Also delete invites made by them.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def ban_with(self, ctx):
        # そのサーバーでログが設定されているか確認
        if not await self.bot.db.is_enabled_guild(ctx.guild.id):
            return await ctx.send(f":warning: Monitoring not enabled!. Please setup by `{self.bot.PREFIX}enable` command before using this feature.")
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
            if invite not in self.bot.cache[ctx.guild.id]:
                error_msg += f":x: `{invite}` is invalid invite code.\n"
            else:
                target_invites.add(invite)
                target_users.add(self.bot.cache[ctx.guild.id][invite]["author"])
        # 指定されたユーザーに招待された人のIDのリストを作成
        for user in await self.bot.db.get_guild_users(ctx.guild.id):
            # 招待者がメンションリストに含まれるか、招待コードが招待コードリストに含まれる場合
            if (await self.bot.db.get_user_invite_from(ctx.guild.id, user) in mentions) or (await self.bot.db.get_user_invite_code(ctx.guild.id, user) in target_invites):
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
            return await ctx.send(f"{self.bot.static_data.emoji.no_mag} No user found.")
        for invite in await ctx.guild.invites():
            if (str(invite.inviter.id) in target_checked) or (invite.code in invites):
                await invite.delete()
        mentions_text = "<@" + "> <@".join(target_checked) + ">"
        await ctx.send(f":magic_wand: {mentions_text[:1900].rsplit('<', 1)[0] + '...' if len(mentions_text) >= 1900 else mentions_text} has banned successfully!")


def setup(bot):
    bot.add_cog(Manage(bot))
