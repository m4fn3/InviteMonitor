from discord.ext import commands
import discord, asyncio
from main import InvStat

class Cache(commands.Cog):
    """__Clear cached datas__"""

    def __init__(self, bot):
        self.bot = bot  # type: InvStat

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f":hourglass_flowing_sand: Interval too fast!\nYou can use this command again __**after {error.retry_after:.2f} sec!**__")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(":placard: Missing required arguments!")
        else:
            await ctx.send(f":tools: Unexpected error has occurred. please contact to bot developer.\n```py{error[:1900]}```")

    @commands.command(aliases=["clear_invite"], usage="clear_invites (@user)", description="Delete invite url/codes made by mentioned user. If no user mentioned, delete all invite url/codes of the server.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def clear_invites(self, ctx):
        # 設定前に権限を確認
        if not self.bot.check_permission(ctx.guild.me):
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(":no_entry_sign: Missing required permission **__manage_guild__**!\nPlease make sure that BOT has right access.")
        if not self.bot.check_permission(ctx.author):
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(":no_pedestrians: You don't have **__manage_guild__** permisson!\nFor security reasons, this command can only be used by person who have permission.")
        if not ctx.message.mentions:  # 全員分
            await ctx.send(f":warning: **ARE YOU REALLY WANT TO DELETE ALL INVITE URLS OF THE SERVER?**\nType '**yes**' to continue.")

            def check(m):
                return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

            try:
                msg = await self.bot.wait_for('message', check=check, timeout=30)
                if msg.content not in ["yes", "y", "'yes'"]:
                    return await ctx.send(":negative_squared_cross_mark: Command canceled!")
            except asyncio.TimeoutError:
                return await ctx.send(":negative_squared_cross_mark: Command canceled because no text provided for a long time.")
            await ctx.send(f"{self.bot.datas['emojis']['loading']} It may takes several time if the server is large..")
            for invite in await ctx.guild.invites():
                await invite.delete()
            await ctx.send(":recycle: All server invites has deleted successfully!")
        else:  # 特定ユーザー分
            target_users = {user.id for user in ctx.message.mentions}
            for invite in await ctx.guild.invites():
                if invite.inviter.id in target_users:
                    await invite.delete()
            mentions_text = "<@" + "> <@".join(target_users) + ">"
            await ctx.send(f":recycle: All server invites created by {mentions_text[:1900].rsplit('<', 1)[0] + '...' if len(mentions_text) >= 1900 else mentions_text} has deleted successfully!")

    @commands.command(aliases=["clear_caches"], usage="clear_cache (@user)", description="Delete invited counts data of mentioned user. If no user mentioned, delete data of all server members.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def clear_cache(self, ctx):
        # 設定前に権限を確認
        if not self.bot.check_permission(ctx.author):
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(":no_pedestrians: You don't have **__manage_guild__** permission!\nFor security reasons, this command can only be used by person who have permission.")
        if not ctx.message.mentions:  # 全員分
            await ctx.send(f":warning: **ARE YOU REALLY WANT TO DELETE INVITED COUNTS DATA OF ALL SERVER MEMBERS?**\nType '**yes**' to continue.")

            def check(m):
                return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=30)
                if msg.content not in ["yes", "y", "'yes'"]:
                    return await ctx.send(":negative_squared_cross_mark: Command canceled!")
            except asyncio.TimeoutError:
                return await ctx.send(":negative_squared_cross_mark: Command canceled because no text provided for a long time.")
            await ctx.send(f"{self.bot.datas['emojis']['loading']} It may takes several time if the server is large..")
            for user in self.bot.db[str(ctx.guild.id)]["users"]:
                self.bot.db[str(ctx.guild.id)]["users"][user]["to"] = set()
                self.bot.db[str(ctx.guild.id)]["users"][user]["to_all"] = set()
            await ctx.send(":recycle: All cached data has deleted successfully!")
        else:  # 特定ユーザー分
            target_users = []
            for target_user in ctx.message.mentions:
                target_users.append(str(target_user.id))
                if str(target_user.id) in self.bot.db[str(ctx.guild.id)]["users"]:
                    self.bot.db[str(ctx.guild.id)]["users"][str(target_user.id)]["to"] = set()
                    self.bot.db[str(ctx.guild.id)]["users"][str(target_user.id)]["to_all"] = set()
            mentions_text = "<@" + "> <@".join(target_users) + ">"
            await ctx.send(f":recycle: All cached data of {mentions_text[:1900].rsplit('<', 1)[0] + '...' if len(mentions_text) >= 1900 else mentions_text} has deleted successfully!")

def setup(bot):
    bot.add_cog(Cache(bot))
