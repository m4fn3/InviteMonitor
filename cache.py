from discord.ext import commands

from main import InviteMonitor

import identifier
from identifier import error_embed_builder, warning_embed_builder

class Cache(commands.Cog):
    """Clear cached data"""

    def __init__(self, bot):
        self.bot = bot  # type: InviteMonitor

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await error_embed_builder(ctx, f"Interval too fast!\nYou can use this command again __**after {error.retry_after:.2f} sec!**__")
        elif isinstance(error, commands.MissingRequiredArgument):
            await error_embed_builder(ctx, "Missing required arguments!")
        elif isinstance(error, commands.CheckFailure):
            pass
        else:
            await error_embed_builder(ctx, f":tools: Unexpected error has occurred. please contact to bot developer.\n```py\n{str(error)[:1900]}```")

    @identifier.is_has_manage_guild()
    @commands.command(aliases=["clear_invite"], brief="Clear invites", usage="clear_invites (@user)", description="Delete invites made by mentioned user. If no user mentioned, delete all invite url/codes of the server.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def clear_invites(self, ctx):
        if not ctx.message.mentions:  # 全員分
            await warning_embed_builder(ctx, "Are you really want to delete all invites?\n\nFollowing data will be deleted:\n・All server invites", "Type 'yes' to continue.")
            if not await self.bot.confirm(ctx):
                return
            await ctx.send(f"{self.bot.static_data.emoji.loading} It may takes several time if the server is large..")
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

    @identifier.is_author_has_manage_guild()
    @commands.command(aliases=["clear_caches"], brief="Clear caches", usage="clear_cache (@user)", description="Delete invited counts data of mentioned user. If no user mentioned, delete data of all server members.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def clear_cache(self, ctx):
        if not ctx.message.mentions:  # 全員分
            await warning_embed_builder(ctx, "Are you really want to delete all caches?\n\nFollowing data will be deleted:\n・Invite counts of all user", "Type 'yes' to continue.")
            if not await self.bot.confirm(ctx):
                return
            await ctx.send(f"{self.bot.static_data.emoji.loading} It may takes several time if the server is large..")
            for user in await self.bot.db.get_guild_users(ctx.guild.id):
                await self.bot.db.reset_user_data(ctx.guild.id, user)
            await ctx.send(":recycle: All cached data has deleted successfully!")
        else:  # 特定ユーザー分
            target_users = []
            for target_user in ctx.message.mentions:
                target_users.append(str(target_user.id))
                if str(target_user.id) in await self.bot.db.get_guild_users(ctx.guild.id):
                    await self.bot.db.reset_user_data(ctx.guild.id, target_user.id)
            mentions_text = "<@" + "> <@".join(target_users) + ">"
            await ctx.send(f":recycle: All cached data of {mentions_text[:1900].rsplit('<', 1)[0] + '...' if len(mentions_text) >= 1900 else mentions_text} has deleted successfully!")


def setup(bot):
    bot.add_cog(Cache(bot))
