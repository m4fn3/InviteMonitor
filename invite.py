from discord.ext import commands
import asyncio, discord, traceback2, datetime, pytz
from main import InvStat

class Invite(commands.Cog):
    """__Manage invites__"""
    def __init__(self, bot):
        self.bot = bot  # type: InvStat

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f":hourglass_flowing_sand: Interval too fast!\nYou can use this command again __**after {error.retry_after:.2f} sec!**__")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(":placard: Missing required arguments!")
        else:
            await ctx.send(f":tools: Unexpected error has occurred. please contact to bot developer.\n```py{error[:1900]}```")

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        if (target_channel := self.bot.db[str(invite.guild.id)]["channel"]) is not None:
            if self.bot.check_permission(invite.guild.me):
                await self.bot.update_server_cache(invite.guild)
                embed = discord.Embed(title=f"{self.bot.datas['emojis']['invite_add']} Invite Created", color=0x00ff7f)
                embed.description = f"Invite [{invite.code}]({invite.url}) has been created by <@{invite.inviter.id}>"
                embed.add_field(name="Channel", value=f"<#{invite.channel.id}>")  # Object型になる可能性があるので
                embed.add_field(name="MaxUses / MaxAge", value=f"{self.parse_max_uses(invite.max_uses)} times | {self.parse_max_age(invite.max_age)}")
                embed.add_field(name="Inviter", value=f"{invite.inviter}")
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
                if (user := self.bot.get_user(inviter)) is None:
                    try:
                        user = await self.bot.fetch_user(inviter)
                    except:
                        user = "Unknown"
                embed.add_field(name="Inviter", value=f"{user}")
                await self.bot.get_channel(target_channel).send(embed=embed)
                # InviteRoleに登録されたコードが削除されていないかどうか確認する
                if invite.code in self.bot.db[str(invite.guild.id)]["roles"]["code"]:
                    await self.bot.get_channel(target_channel).send(f":warning: Invite `{invite.code}` was deleted, so this trigger is no longer available!")
                    del self.bot.db[str(invite.guild.id)]["roles"]["code"][invite.code]  # 削除する

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
                            "from": None,
                            "code": None
                        }
                    else:
                        self.bot.db[str(member.guild.id)]["users"][str(res[0])]["to"].add(member.id)
                        self.bot.db[str(member.guild.id)]["users"][str(res[0])]["to_all"].add(member.id)
                    # 招待された人の招待作成者を記録
                    if str(member.id) not in self.bot.db[str(member.guild.id)]["users"]:
                        self.bot.db[str(member.guild.id)]["users"][str(member.id)] = {
                            "to_all": set(),
                            "to": set(),
                            "from": res[0],
                            "code": res[1]
                        }
                    else:
                        self.bot.db[str(member.guild.id)]["users"][str(member.id)]["from"] = res[0]
                        self.bot.db[str(member.guild.id)]["users"][str(member.id)]["code"] = res[1]
                    if (inviter := self.bot.get_user(res[0])) is None:
                        try:
                            inviter = await self.bot.fetch_user(res[0])
                        except:
                            inviter = "Unknown"
                    embed.description = f"<@{member.id}> has joined through [{res[1]}](https://discord.gg/{res[1]}) made by <@{inviter.id}>"
                    embed.add_field(name="User", value=f"{member}")
                    embed.add_field(name="Invite", value=f"{res[1]} | {inviter}")
                else:
                    embed.description = f"<@{member.id}> has joined"
                    embed.add_field(name="User", value=f"{member}")
                    embed.add_field(name="Invite", value=f"Unknown")
                now = datetime.datetime.now(datetime.timezone.utc)
                embed.timestamp = now
                delta = now - pytz.timezone('UTC').localize(member.created_at)
                if delta.days == 0:
                    delta = f"__**{delta.seconds // 3600}hours {(delta.seconds % 3600) // 60}minutes**__"
                elif delta.days <= 7:
                    delta = f"**{delta.days}days {delta.seconds // 3600}hours**"
                else:
                    delta = f"{delta.days // 30}months {delta.seconds % 30}days"
                embed.add_field(name="Account Created", value=f"{delta} ago", inline=False)
                embed.set_footer(text=f"{member.guild.name} | {len(member.guild.members)}members", icon_url=member.guild.icon_url)
                await self.bot.get_channel(target_channel).send(embed=embed)
                if member.guild.me.guild_permissions.manage_roles:  # ロール管理権限がある場合
                    if res[0] in self.bot.db[str(member.guild.id)]["roles"]["user"]:  # 招待者が設定されている場合
                        role_id = self.bot.db[str(member.guild.id)]["roles"]["user"][res[0]]
                        target_role = member.guild.get_role(role_id)
                        if target_role is None:  # 役職を取得できない場合
                            await self.bot.get_channel(target_channel).send(f":warning: Role `{role_id}` was not found, so this trigger is no longer available!")
                            del self.bot.db[str(member.guild.id)]["roles"]["user"][res[0]]  # 削除する
                        else:
                            try:
                                await member.add_roles(target_role)
                            except:
                                pass
                    elif res[1] in self.bot.db[str(member.guild.id)]["roles"]["code"]:
                        role_id = self.bot.db[str(member.guild.id)]["roles"]["code"][res[1]]
                        target_role = member.guild.get_role(role_id)
                        if target_role is None:  # 役職を取得できない場合
                            await self.bot.get_channel(target_channel).send(f":warning: Role `{role_id}` was not found, so this trigger is no longer available!")
                            del self.bot.db[str(member.guild.id)]["roles"]["code"][res[1]]  # 削除する
                        else:
                            try:
                                await member.add_roles(target_role)
                            except:
                                pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if (target_channel := self.bot.db[str(member.guild.id)]["channel"]) is not None:
            if self.bot.check_permission(member.guild.me):
                embed = discord.Embed(title=f"{self.bot.datas['emojis']['member_leave']} Member Left", color=0xff1493)
                embed.set_thumbnail(url=member.avatar_url)
                # メンバーがデータベース上に存在しないか、招待元がNoneの場合
                if (str(member.id) not in self.bot.db[str(member.guild.id)]["users"]) or (self.bot.db[str(member.guild.id)]["users"][str(member.id)]["from"] is None):
                    embed.description = f"<@{member.id}> has left"
                    embed.add_field(name="User", value=f"{member}")
                    embed.add_field(name="Invite", value=f"Unknown")
                else:
                    inviter_id = self.bot.db[str(member.guild.id)]["users"][str(member.id)]["from"]
                    invite_code = self.bot.db[str(member.guild.id)]["users"][str(member.id)]["code"]
                    # 招待者がデータに登録されており、招待者の招待先にその人が登録されているなら、現在も入っているメンバーのリストから削除
                    if str(inviter_id) in self.bot.db[str(member.guild.id)]["users"] and member.id in self.bot.db[str(member.guild.id)]["users"][str(inviter_id)]["to"] and member.id in self.bot.db[str(member.guild.id)]["users"][str(inviter_id)]["to_all"]:
                        self.bot.db[str(member.guild.id)]["users"][str(inviter_id)]["to"].remove(member.id)
                    if (inviter := self.bot.get_user(inviter_id)) is None:
                        try:
                            inviter = await self.bot.fetch_user(inviter_id)
                        except:
                            inviter = "Unknown"
                    embed.description = f"<@{member.id}> invited by <@{inviter.id}> has left"
                    embed.add_field(name="User", value=f"{member}")
                    embed.add_field(name="Invite", value=f"{invite_code} | {inviter}")
                now = datetime.datetime.now(datetime.timezone.utc)
                embed.timestamp = now
                delta = now - pytz.timezone('UTC').localize(member.joined_at)
                if delta.days == 0:
                    delta = f"{delta.seconds // 3600}hours {(delta.seconds % 3600) // 60}minutes"
                elif delta.days <= 7:
                    delta = f"{delta.days}days {delta.seconds // 3600}hours"
                else:
                    delta = f"{delta.days // 30}months {delta.seconds % 30}days"
                embed.add_field(name="Stayed Time", value=f"{delta}", inline=False)
                embed.set_footer(text=f"{member.guild.name} | {len(member.guild.members)}members", icon_url=member.guild.icon_url)
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

    @commands.group()
    async def invite_role(self, ctx):
        pass  # リストを表示

    @invite_role.command(name="user", aliase=["inviter"])
    async def invite_role_user(self, ctx, user_id, role_id):
        pass  # 設定する

    @invite_role.command(name="code", aliase=["invite"])
    async def invite_role_code(self, ctx, code, role_id):
        pass  # 設定する

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
