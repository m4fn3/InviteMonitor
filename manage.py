from discord.ext import commands
import discord, traceback2
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
            await ctx.send(f":tools: Unexpected error has occurred. please contact to bot developer.\n```py{error}```")

    @commands.command(usage="kick [@user]", description="Kick the mentioned user and delete invites made by mentioned user")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def kick(self, ctx):
        # 権限を確認
        if not ctx.guild.me.guild_permissions.kick_members:
            return await ctx.send(":no_entry_sign: Missing required permission **__kick_members__**!\nPlease make sure that BOT has right access.")
        if not ctx.author.guild_permissions.kick_members:
            return await ctx.send(":no_pedestrians: You don't have **__kick_members__** permisson!\nFor security reasons, this command can only be used by person who have permission.")
        if not ctx.message.mentions:
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
        await ctx.send(":magic_wand: <@" + "> <@".join(target_users) + "> has kicked successfully!")

    @commands.command(usage="ban [@user]", description="Ban the mentioned user and delete invites made by mentioned user")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def ban(self, ctx):
        # 権限を確認
        if not ctx.guild.me.guild_permissions.kick_members:
            return await ctx.send(":no_entry_sign: Missing required permission **__kick_members__**!\nPlease make sure that BOT has right access.")
        if not ctx.author.guild_permissions.kick_members:
            return await ctx.send(":no_pedestrians: You don't have **__kick_members__** permisson!\nFor security reasons, this command can only be used by person who have permission.")
        if not ctx.message.mentions:
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
        await ctx.send(":magic_wand: <@" + "> <@".join(target_users) + "> has banned successfully!")

    @commands.command(usage="kick_together [@user]", description="Kick the mentioned user and users who invited by mentioned user. Also delete invites made by them.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def kick_together(self, ctx):
        # 権限を確認
        if not ctx.guild.me.guild_permissions.kick_members:
            return await ctx.send(":no_entry_sign: Missing required permission **__kick_members__**!\nPlease make sure that BOT has right access.")
        if not ctx.author.guild_permissions.kick_members:
            return await ctx.send(":no_pedestrians: You don't have **__kick_members__** permisson!\nFor security reasons, this command can only be used by person who have permission.")
        if not ctx.message.mentions:
            return await ctx.send(":warning: Please mention at least one user!")
        mentions = {user.id for user in ctx.message.mentions}
        # 指定されたユーザーに招待された人のIDのリストを作成
        target_users = set()
        for user in self.bot.db[str(ctx.guild.id)]["users"]:
            if self.bot.db[str(ctx.guild.id)]["users"][user]["from"] in mentions:
                target_users.add(int(user))
        target_users = target_users.union(mentions)
        # Kickに成功した人のみのリストを作成
        target_checked = set()
        for target in target_users:
            try:
                await ctx.guild.get_member(target).kick()
            except:
                print(traceback2.format_exc())
                await ctx.send(f":x: Failed to kick user <@{target}>")
            else:
                target_checked.add(str(target))
        if not target_checked:
            return
        for invite in await ctx.guild.invites():
            if str(invite.inviter.id) in target_checked:
                await invite.delete()
        await ctx.send(":magic_wand: <@" + "> <@".join(target_checked) + "> has banned successfully!")

    @commands.command(usage="ban_together [@user]", description="Ban the mentioned user and users who invited by mentioned user. Also delete invites made by them.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def ban_together(self, ctx):
        # 権限を確認
        if not ctx.guild.me.guild_permissions.kick_members:
            return await ctx.send(":no_entry_sign: Missing required permission **__kick_members__**!\nPlease make sure that BOT has right access.")
        if not ctx.author.guild_permissions.kick_members:
            return await ctx.send(":no_pedestrians: You don't have **__kick_members__** permisson!\nFor security reasons, this command can only be used by person who have permission.")
        if not ctx.message.mentions:
            return await ctx.send(":warning: Please mention at least one user!")
        mentions = {user.id for user in ctx.message.mentions}
        # 指定されたユーザーに招待された人のIDのリストを作成
        target_users = set()
        for user in self.bot.db[str(ctx.guild.id)]["users"]:
            if self.bot.db[str(ctx.guild.id)]["users"][user]["from"] in mentions:
                target_users.add(int(user))
        target_users = target_users.union(mentions)
        # BANに成功した人のみのリストを作成
        target_checked = set()
        for target in target_users:
            try:
                await ctx.guild.get_member(target).ban()
            except:
                print(traceback2.format_exc())
                await ctx.send(f":x: Failed to ban user <@{target}>")
            else:
                target_checked.add(str(target))
        if not target_checked:
            return
        for invite in await ctx.guild.invites():
            if str(invite.inviter.id) in target_checked:
                await invite.delete()
        await ctx.send(":magic_wand: <@" + "> <@".join(target_checked) + "> has banned successfully!")


def setup(bot):
    bot.add_cog(Manage(bot))
