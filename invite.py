from discord.ext import commands
import discord
from main import InvStat

class Invite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # type: InvStat

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Interval too fast!\nYou can use this command again __**after {error.retry_after:.2f} sec!**__")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing required argumnts!")

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        if (target_channel := self.bot.db[str(invite.guild.id)]["channel"]) is not None:
            if self.bot.check_permission(invite.guild.me):
                await self.bot.update_server_cache(invite.guild)
                embed = discord.Embed(title="Invite Created", color=0x00ff7f)
                embed.description = f"Invite [{invite.code}]({invite.url}) has been created by [{str(invite.inviter)}]({invite.url})"
                embed.add_field(name="Channel", value=f"<#{invite.channel.id}>")  # Object型になる可能性があるので
                embed.add_field(name="MaxUses", value=f"{invite.max_uses}")
                embed.add_field(name="MaxAge", value=f"{invite.max_age}")
                await self.bot.get_channel(target_channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        if (target_channel := self.bot.db[str(invite.guild.id)]["channel"]) is not None:
            if self.bot.check_permission(invite.guild.me):
                inviter = None
                # キャッシュに存在しない場合を考慮して,場合分けする
                if invite.code in self.bot.cache[str(invite.guild.id)]:
                    inviter = self.bot.cache[str(invite.guild.id)][invite.code]['author']
                await self.bot.update_server_cache(invite.guild)
                embed = discord.Embed(title="Invite Deleted", color=0xff8c00)
                embed.description = f"Invite [{invite.code}]({invite.url}) by [{await self.bot.fetch_user(inviter) if inviter else 'Unknown'}]({invite.url}) has deleted or expired."
                embed.add_field(name="Channel", value=f"<#{invite.channel.id}>")  # Object型になる可能性があるので
                await self.bot.get_channel(target_channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if (target_channel := self.bot.db[str(member.guild.id)]["channel"]) is not None:
            if self.bot.check_permission(member.guild.me):
                old_invite_cache = self.bot.cache[str(member.guild.id)]
                new_invite_cache = await self.bot.update_server_cache(member.guild)
                res = await self.check_invite_diff(old_invite_cache, new_invite_cache)
                embed = discord.Embed(title="Member Joined", color=0x00ffff)
                embed.set_thumbnail(url=member.avatar_url)
                if res is not None:  # ユーザーが判別できた場合
                    # 招待作成者の招待履歴に記録
                    if str(res[0]) not in self.bot.db[str(member.guild.id)]["users"]:
                        self.bot.db[str(member.guild.id)]["users"][str(res[0])] = {
                            "to_all": {member.id},
                            "to": {member.id},
                            "from": None
                        }
                    else:
                        self.bot.db[str(member.guild.id)]["users"][str(res[0])]["to"].add(member.id)
                        self.bot.db[str(member.guild.id)]["users"][str(res[0])]["to_all"].add(member.id)
                    # 招待された人の招待作成者を記録
                    if str(member.id) not in self.bot.db[str(member.guild.id)]["users"]:
                        self.bot.db[str(member.guild.id)]["users"][str(member.id)] = {
                            "to_all": set(),
                            "to": set(),
                            "from": res[0]
                        }
                    else:
                        self.bot.db[str(member.guild.id)]["users"][str(member.id)]["from"] = res[0]
                    if (inviter := self.bot.get_user(res[0])) is None:
                        try:
                            inviter = await self.bot.fetch_user(res[0])
                        except:
                            inviter = "Unknown"
                    embed.description = f"[{member}](https://discord.gg/{res[1]}) has joined through [{res[1]}](https://discord.gg/{res[1]}) made by [{inviter}](https://discord.gg/{res[1]})"
                    embed.add_field(name="User", value=f"{member}")
                    embed.add_field(name="Invite", value=f"{res[1]} - {inviter}")
                else:
                    embed.description = f"[{member}](https://discord.com) has joined"
                    embed.add_field(name="User", value=f"{member}")
                    embed.add_field(name="Invite", value=f"Unknown")
                await self.bot.get_channel(target_channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if (target_channel := self.bot.db[str(member.guild.id)]["channel"]) is not None:
            if self.bot.check_permission(member.guild.me):
                embed = discord.Embed(title="Member Left", color=0xff1493)
                embed.set_thumbnail(url=member.avatar_url)
                if (str(member.id) not in self.bot.db[str(member.guild.id)]["users"]) or (self.bot.db[str(member.guild.id)]["users"][str(member.id)]["from"] is None):
                    embed.description = f"[{member}](https://discord.com) has left"
                    embed.add_field(name="User", value=f"{member}")
                    embed.add_field(name="Invite", value=f"Unknown")
                else:
                    inviter_id = self.bot.db[str(member.guild.id)]["users"][str(member.id)]["from"]
                    if str(inviter_id) in self.bot.db[str(member.guild.id)]["users"] and member.id in self.bot.db[str(member.guild.id)]["users"][str(inviter_id)]["to"] and member.id in self.bot.db[str(member.guild.id)]["users"][str(inviter_id)]["to_all"]:
                        self.bot.db[str(member.guild.id)]["users"][str(inviter_id)]["to"].remove(member.id)
                    if (inviter := self.bot.get_user(inviter_id)) is None:
                        try:
                            inviter = await self.bot.fetch_user(inviter_id)
                        except:
                            inviter = "Unknown"
                    embed.description = f"[{member}](https://discord.com) invited by [{inviter}](https://discord.com) has left"
                    embed.add_field(name="User", value=f"{member}")
                    embed.add_field(name="Invite", value=f"{inviter}")
                await self.bot.get_channel(target_channel).send(embed=embed)

    @commands.Cog.listener()
    async def check_invite_diff(self, old_invites, new_invites):
        for invite in old_invites:
            if invite in new_invites:
                if old_invites[invite] != new_invites[invite]:
                    return [old_invites[invite]["author"], invite]  # 使用回数が変わっている場合
            else:
                return [old_invites[invite]["author"], invite]  # 招待コードがなくなっている場合→使用上限回数に達した場合
        else:
            return None  # 何らかの問題で,変更点が見つからなかった場合

    @commands.command(aliases=["su", "set_up", "set-up"])
    async def setup(self, ctx):
        # 設定前に権限を確認
        if not self.bot.check_permission(ctx.guild.me):
            return await ctx.send("Missing required permission **__manage_guild__**!\nPlease make sure that BOT has right access.")
        if not self.bot.check_permission(ctx.author):
            return await ctx.send("You don't have **__manage_guild__** permisson!\nFor security reasons, this command can only be used by person who have permission.")
        # 対象チャンネルを取得
        target_channel: discord.TextChannel
        if not len(ctx.message.channel_mentions):
            target_channel = ctx.channel
        else:
            target_channel = ctx.message.channel_mentions[0]
        # チャンネルデータを保存
        self.bot.db[str(ctx.guild.id)]["channel"] = target_channel.id
        await ctx.send(f"Log channel has been set to {target_channel.mention} successfully!")

    @commands.command(aliases=["st"])
    async def status(self, ctx):
        # そのサーバーでログが設定されているか確認
        if self.bot.db[str(ctx.guild.id)]["channel"] is None:
            return await ctx.send("Log channel haven't set yet. Please select channel and available cool features by __**i/setup #チャンネル**__")
        if not ctx.message.mentions:
            # 設定を取得
            embed = discord.Embed(title="Log Settings Status", color=0x9932cc)
            embed.set_thumbnail(url=ctx.guild.icon_url)
            embed.description = f"Status of the server **{ctx.guild.name}**"
            embed.add_field(name="Log Channel", value=f"<#{self.bot.db[str(ctx.guild.id)]['channel']}>")
            embed.add_field(name="Member Count", value=f"{len(ctx.guild.members)}")
            embed.add_field(name="Known Members", value=f"{len(self.bot.db[str(ctx.guild.id)]['users'])}")
            embed.add_field(name="Invites Count", value=f"{len(self.bot.cache[str(ctx.guild.id)])}")
            await ctx.send(embed=embed)
        else:
            target_user = ctx.message.mentions[0]
            embed = discord.Embed(title=str(target_user), color=0xffff00)
            embed.set_thumbnail(url=target_user.avatar_url)
            if str(target_user.id) in self.bot.db[str(ctx.guild.id)]["users"]:
                remain_count = 0
                if self.bot.db[str(ctx.guild.id)]["users"][str(target_user.id)]["to"] is not None:
                    remain_count = len(self.bot.db[str(ctx.guild.id)]["users"][str(target_user.id)]["to"])
                total_count = 0
                if self.bot.db[str(ctx.guild.id)]["users"][str(target_user.id)]["to_all"] is not None:
                    total_count = len(self.bot.db[str(ctx.guild.id)]["users"][str(target_user.id)]["to_all"])
                embed.add_field(name="Invite Count", value=f"{remain_count} / {total_count}")
                if (inviter_id := self.bot.db[str(ctx.guild.id)]["users"][str(target_user.id)]["from"]) is not None:
                    if (inviter := self.bot.get_user(inviter_id)) is None:
                        try:
                            inviter = await self.bot.fetch_user(inviter_id)
                        except:
                            inviter = "Unknown"
                    embed.add_field(name="Invited By", value=str(inviter))
                else:
                    embed.add_field(name="Invited By", value="Unknown")
            else:
                embed.add_field(name="Invite Count", value="0 / 0")
                embed.add_field(name="Invited By", value="Unknown")
            embed.add_field(name="Joined At", value=ctx.guild.get_member(target_user.id).joined_at.strftime("%Y/%m/%d %H:%M:%S"))
            await ctx.send(embed=embed)

    @commands.command(aliases=["inv"])
    async def invite(self, ctx):
        await ctx.send(f"__**Add {self.bot.user.name}**__\n{self.bot.datas['invite']}\n__**Enter Official Server**__\n{self.bot.datas['server']}")

    @commands.command(aliases=["ci"])
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def clear_invites(self, ctx):
        # 設定前に権限を確認
        if not self.bot.check_permission(ctx.guild.me):
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("Missing required permission **__manage_guild__**!\nPlease make sure that BOT has right access.")
        if not self.bot.check_permission(ctx.author):
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("You don't have **__manage_guild__** permisson!\nFor security reasons, this command can only be used by person who have permission.")
        if not ctx.message.mentions:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("Please mention the user that want to clear invites!")
        target_user = ctx.message.mentions[0]
        for invite in await ctx.guild.invites():
            if invite.inviter.id == target_user.id:
                await invite.delete()
        await ctx.send(f"All server invites created by **{target_user}** has deleted successfully!")

    @commands.command(aliases=["cai"])
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def clear_all_invites(self, ctx):
        if not self.bot.check_permission(ctx.guild.me):
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("Missing required permission **__manage_guild__**!\nPlease make sure that BOT has right access.")
        if not self.bot.check_permission(ctx.author):
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("You don't have **__manage_guild__** permisson!\nFor security reasons, this command can only be used by person who have permission.")
        await ctx.send("It may takes several time if the server is big..")
        for invite in await ctx.guild.invites():
            await invite.delete()
        await ctx.send("All server invites has deleted successfully!")

    @commands.command(aliases=["cc"])
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def clear_cache(self, ctx):
        if not self.bot.check_permission(ctx.author):
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("You don't have **__manage_guild__** permisson!\nFor security reasons, this command can only be used by person who have permission.")
        if not ctx.message.mentions:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("Please mention the user that want to clear cache!")
        target_user = ctx.message.mentions[0]
        if str(target_user.id) in self.bot.db[str(ctx.guild.id)]["users"]:
            self.bot.db[str(ctx.guild.id)]["users"][str(target_user.id)]["to"] = set()
            self.bot.db[str(ctx.guild.id)]["users"][str(target_user.id)]["to_all"] = set()
            await ctx.send(f"All cached data of **{target_user}** has deleted successfully!")
        else:
            await ctx.sedn("There is no cached data for this user yet!")

    @commands.command(aliases=["cac"])
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def clear_all_cache(self, ctx):
        if not self.bot.check_permission(ctx.author):
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("You don't have **__manage_guild__** permisson!\nFor security reasons, this command can only be used by person who have permission.")
        await ctx.send("It may takes several time if the server is big..")
        for user in self.bot.db[str(ctx.guild.id)]["users"]:
            self.bot.db[str(ctx.guild.id)]["users"][user]["to"] = set()
            self.bot.db[str(ctx.guild.id)]["users"][user]["to_all"] = set()
        await ctx.send("All cached data has deleted successfully!")

def setup(bot):
    bot.add_cog(Invite(bot))
