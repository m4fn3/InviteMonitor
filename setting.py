import datetime
import time

import discord
from discord.ext import commands

import identifier
from identifier import error_embed_builder, success_embed_builder, warning_embed_builder
from main import InviteMonitor


class Setting(commands.Cog):
    """SetUp the bot"""

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

    @identifier.is_has_manage()
    @commands.command(usage="enable (#channel)", brief="Start monitoring", description="Start monitor invites and report logs to specified channel. If no channel provided, set to channel command executed.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def enable(self, ctx):
        # 対象チャンネルを取得
        target_channel: discord.TextChannel
        if not len(ctx.message.channel_mentions):
            target_channel = ctx.channel
        else:
            target_channel = ctx.message.channel_mentions[0]
        # 権限を確認
        perms = target_channel.permissions_for(ctx.guild.me)
        if not (perms.send_messages and perms.embed_links and perms.read_messages):
            return await error_embed_builder(ctx, f"Missing `read_messages, send_messages, embed_links` permissions in <#{target_channel.id}>")
        # チャンネルデータを保存
        await self.bot.db.enable_guild(ctx.guild.id, target_channel.id)
        await self.bot.update_server_cache(ctx.guild)  # 招待キャッシュを作成
        await success_embed_builder(ctx, f"Log channel has been set to {target_channel.mention} successfully!\nNow started to monitor invites and report logs.")

    @identifier.is_has_manage()
    @commands.command(usage="disable", brief="Stop monitoring", description="Stop monitoring and reporting information in the server.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def disable(self, ctx):
        # 有効化されているか確認
        if not await self.bot.db.is_enabled_guild(ctx.guild.id):
            await error_embed_builder(ctx, "Not enabled yet.")
        else:
            await self.bot.db.disable_guild(ctx.guild.id)
            await success_embed_builder(ctx, f"Stopped monitoring and reporting information.\nYou can resume with `{self.bot.PREFIX}enable` at any time!")
            del self.bot.cache[ctx.guild.id]  # 招待キャッシュの削除

    @commands.command(aliases=["st"], brief="See cached status", usage="status (@user)", description="Show user's data includes inviter and invite counts. If no user mentioned, server status will be shown.")
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def status(self, ctx):
        # そのサーバーでログが設定されているか確認
        if not await self.bot.db.is_enabled_guild(ctx.guild.id):
            return await warning_embed_builder(ctx, f"Not enabled yet. Please setup by `{self.bot.PREFIX}enable` before checking status.")
        if not ctx.message.mentions:
            # 設定を取得
            embed = discord.Embed(color=0xd3a8ff)
            embed.set_author(name=f"{ctx.guild.name}", icon_url=ctx.guild.icon.url)
            embed.set_thumbnail(url=ctx.guild.icon.url)
            embed.description = f"Cached status of the server **{ctx.guild.name}**\n\n"
            embed.description += f"`LogChannel :`  <#{await self.bot.db.get_log_channel_id(ctx.guild.id)}>\n"
            embed.description += f"`Member     :`  {len(ctx.guild.members)}\n"
            embed.description += f"`KnownMember:`  {await self.bot.db.get_guild_users_count(ctx.guild.id)}\n"
            embed.description += f"`Invites    :`  {len(self.bot.cache[ctx.guild.id])}\n"
            embed.description += f"`VerifyLevel:`  [{ctx.guild.verification_level}](https://support.discord.com/hc/ja/articles/216679607-What-are-Verification-Levels-)"
            await ctx.send(embed=embed)
        else:
            target_user = ctx.message.mentions[0]
            embed = discord.Embed(color=0xd3a8ff)
            embed.set_author(name=f"{str(target_user)}", icon_url=target_user.display_avatar.url)
            embed.set_thumbnail(url=target_user.display_avatar.url)
            embed.description = f"Cached data of <@{target_user.id}>\n\n"
            if str(target_user.id) in await self.bot.db.get_guild_users(ctx.guild.id):
                embed.description += f"`InviteCount:`  {await self.bot.db.get_user_invite_count(ctx.guild.id, target_user.id)}\n"
                if inviter_id := await self.bot.db.get_user_invite_from(ctx.guild.id, target_user.id):
                    if (inviter := self.bot.get_user(inviter_id)) is None:
                        try:
                            inviter = await self.bot.fetch_user(inviter_id)
                        except:
                            inviter = "Unknown"
                    embed.description += f"`Inviter    :`  {inviter}\n"
                else:
                    embed.description += f"`Inviter    :`  Unknown\n"
                if used_code := await self.bot.db.get_user_invite_code(ctx.guild.id, target_user.id):
                    embed.description += f"`Used Code  :`  {used_code}\n"
            else:
                embed.description += f"`InviteCount:`  0\n"
                embed.description += f"`Inviter    :`  Unknown\n"
            embed.description += f"`Joined At  :`  {ctx.guild.get_member(target_user.id).joined_at.strftime('%Y/%m/%d %H:%M:%S')}"
            await ctx.send(embed=embed)

    @commands.command(aliases=["info"], usage="about", brief="About the bot", description="Show the information about the bot.")
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def about(self, ctx):
        embed = discord.Embed(title=f"About {self.bot.user.name}", color=0xffffa8)
        embed.description = f"**Thank you for using {self.bot.user.name}!**\n{self.bot.user.name} is strong server monitoring bot that allows you to protects your server from malicious users and keep safety!\n\n"
        embed.description += f"`Servers :`  {len(self.bot.guilds)}\n`Users   :`  {len(self.bot.users)}\n"
        td = datetime.timedelta(seconds=int(time.time() - self.bot.uptime))
        m, s = divmod(td.seconds, 60)
        h, m = divmod(m, 60)
        d = td.days
        embed.description += f"`Uptime  :`  {d}d {h}h {m}m {s}s"
        embed.add_field(name="links📎", value=f"[InviteMe]({self.bot.static_data.invite}) | [SupportServer]({self.bot.static_data.server}) | [VoteMe]({self.bot.static_data.top_gg}) | [Donation]({self.bot.static_data.donate})", inline=False)
        embed.set_footer(text=f"Powered by {self.bot.get_user(self.bot.static_data.author)} with discord.py", icon_url="https://cdn.discordapp.com/emojis/769855038964891688.png")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Setting(bot))
