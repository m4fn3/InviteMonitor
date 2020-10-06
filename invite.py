from discord.ext import commands
import asyncio, discord, traceback2
from main import InvStat

class Invite(commands.Cog):
    """__Manage invites__"""
    def __init__(self, bot):
        self.bot = bot  # type: InvStat

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Interval too fast!\nYou can use this command again __**after {error.retry_after:.2f} sec!**__")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing required argumnts!")
        else:
            await ctx.send(f"Unexpected error has occured. please contact to bot develpoer.\n{error}")

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        if (target_channel := self.bot.db[str(invite.guild.id)]["channel"]) is not None:
            if self.bot.check_permission(invite.guild.me):
                await self.bot.update_server_cache(invite.guild)
                embed = discord.Embed(title=f"{self.bot.datas['emojis']['invite_add']} Invite Created", color=0x00ff7f)
                embed.description = f"Invite [{invite.code}]({invite.url}) has been created by <@{invite.inviter.id}>"
                embed.add_field(name="Channel", value=f"<#{invite.channel.id}>")  # Object型になる可能性があるので
                embed.add_field(name="MaxUses", value=f"{self.parse_max_uses(invite.max_uses)}")
                embed.add_field(name="MaxAge", value=f"{self.parse_max_age(invite.max_age)}")
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
                embed = discord.Embed(title=f"{self.bot.datas['emojis']['invite_del']} Invite Deleted", color=0xff8c00)
                embed.description = f"Invite [{invite.code}]({invite.url}) by {'<@'+str(inviter)+'>' if inviter else 'Unknown'} has deleted or expired."
                embed.add_field(name="Channel", value=f"<#{invite.channel.id}>")  # Object型になる可能性があるので
                await self.bot.get_channel(target_channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if (target_channel := self.bot.db[str(member.guild.id)]["channel"]) is not None:
            if self.bot.check_permission(member.guild.me):
                old_invite_cache = self.bot.cache[str(member.guild.id)]
                new_invite_cache = await self.bot.update_server_cache(member.guild)
                res = await self.check_invite_diff(old_invite_cache, new_invite_cache)
                embed = discord.Embed(title=f"{self.bot.datas['emojis']['member_join']} Member Joined", color=0x00ffff)
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
                    embed.description = f"<@{member.id}> has joined through [{res[1]}](https://discord.gg/{res[1]}) made by <@{inviter.id}>"
                    embed.add_field(name="User", value=f"{member}")
                    embed.add_field(name="Invite", value=f"{res[1]} - {inviter}")
                else:
                    embed.description = f"<@{member.id}> has joined"
                    embed.add_field(name="User", value=f"{member}")
                    embed.add_field(name="Invite", value=f"Unknown")
                await self.bot.get_channel(target_channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if (target_channel := self.bot.db[str(member.guild.id)]["channel"]) is not None:
            if self.bot.check_permission(member.guild.me):
                embed = discord.Embed(title=f"{self.bot.datas['emojis']['member_leave']} Member Left", color=0xff1493)
                embed.set_thumbnail(url=member.avatar_url)
                if (str(member.id) not in self.bot.db[str(member.guild.id)]["users"]) or (self.bot.db[str(member.guild.id)]["users"][str(member.id)]["from"] is None):
                    embed.description = f"<@{member.id}> has left"
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
                    embed.description = f"<@{member.id}> invited by <@{inviter.id}> has left"
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

    @commands.command(aliases=["inv"], usage="invite (@bot)", description="Show invite URL of this BOT. If bot mentioned, send invite url of mentioned bot")
    async def invite(self, ctx):
        if not ctx.message.mentions:
            await ctx.send(f"__**Add {self.bot.user.name}!**__\n{self.bot.datas['invite']}\n__**Join Official Server!**__\n{self.bot.datas['server']}")
        else:
            invite_text = ""
            for target_user in ctx.message.mentions:
                if target_user.bot:
                    new_invite_text = f"__**{str(target_user)} 's invite link**__\nhttps://discord.com/oauth2/authorize?client_id={target_user.id}&scope=bot&permissions=-8\n"
                else:
                    new_invite_text = f"{target_user} is not the bot!\n"
                if len(invite_text+new_invite_text) > 1900:
                    invite_text += "(Some invites have been omitted due to message length limit)"
                    break
                else:
                    invite_text += new_invite_text
            await ctx.send(invite_text)

    @commands.command(aliases=["clear_invite"], usage="clear_invites (@user)", description="Delete invite url/codes made by mentioned user. If no user mentioned, delete all invite url/codes of the server.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def clear_invites(self, ctx):
        # 設定前に権限を確認
        if not self.bot.check_permission(ctx.guild.me):
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("Missing required permission **__manage_guild__**!\nPlease make sure that BOT has right access.")
        if not self.bot.check_permission(ctx.author):
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("You don't have **__manage_guild__** permisson!\nFor security reasons, this command can only be used by person who have permission.")
        if not ctx.message.mentions:  # 全員分
            await ctx.send(f":warning: **ARE YOU REALLY WANT TO DELETE ALL INVITE URLS OF THE SERVER?**\nType '**yes**' to continue.")

            def check(m):
                return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

            try:
                msg = await self.bot.wait_for('message', check=check, timeout=30)
                if msg.content not in ["yes", "y", "'yes'"]:
                    return await ctx.send("Command canceled!")
            except asyncio.TimeoutError:
                return await ctx.send("Command canceled because no text provided for a long time.")
            await ctx.send(f"{self.bot.datas['emojis']['loading']} It may takes several time if the server is large..")
            for invite in await ctx.guild.invites():
                await invite.delete()
            await ctx.send("All server invites has deleted successfully!")
        else:  # 特定ユーザー分
            target_user = ctx.message.mentions[0]
            for invite in await ctx.guild.invites():
                if invite.inviter.id == target_user.id:
                    await invite.delete()
            await ctx.send(f"All server invites created by **{target_user}** has deleted successfully!")

    @commands.command(aliases=["clear_caches"], usage="clear_cache (@user)", description="Delete invited counts data of mentioned user. If no user mentioned, delete data of all server members.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def clear_cache(self, ctx):
        # 設定前に権限を確認
        if not self.bot.check_permission(ctx.author):
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("You don't have **__manage_guild__** permission!\nFor security reasons, this command can only be used by person who have permission.")
        if not ctx.message.mentions:  # 全員分
            await ctx.send(f":warning: **ARE YOU REALLY WANT TO DELETE INVITED COUNTS DATA OF ALL SERVER MEMBERS?**\nType '**yes**' to continue.")

            def check(m):
                return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=30)
                if msg.content not in ["yes", "y", "'yes'"]:
                    return await ctx.send("Command canceled!")
            except asyncio.TimeoutError:
                return await ctx.send("Command canceled because no text provided for a long time.")
            await ctx.send(f"{self.bot.datas['emojis']['loading']} It may takes several time if the server is large..")
            for user in self.bot.db[str(ctx.guild.id)]["users"]:
                self.bot.db[str(ctx.guild.id)]["users"][user]["to"] = set()
                self.bot.db[str(ctx.guild.id)]["users"][user]["to_all"] = set()
            await ctx.send("All cached data has deleted successfully!")
        else:  # 特定ユーザー分
            target_user = ctx.message.mentions[0]
            if str(target_user.id) in self.bot.db[str(ctx.guild.id)]["users"]:
                self.bot.db[str(ctx.guild.id)]["users"][str(target_user.id)]["to"] = set()
                self.bot.db[str(ctx.guild.id)]["users"][str(target_user.id)]["to_all"] = set()
                await ctx.send(f"All cached data of **{target_user}** has deleted successfully!")
            else:
                await ctx.send("There is no cached data for this user yet!")

    def parse_max_uses(self, max_uses: int) -> str:
        if max_uses == 0:
            return "∞"
        else:
            return str(max_uses)

    def parse_max_age(self, max_age: int) -> str:
        if max_age == 0:
            return "∞"
        elif max_age == 1800:
            return "30 minutes"
        elif max_age == 3600:
            return "1 hour"
        elif max_age == 21600:
            return "6 hours"
        elif max_age == 43200:
            return "12 hours"
        elif max_age == 86400:
            return "1 day"


def setup(bot):
    bot.add_cog(Invite(bot))
