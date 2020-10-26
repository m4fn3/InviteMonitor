import datetime
import re

import discord
import pytz
from discord.ext import commands

import identifier
from identifier import error_embed_builder, warning_embed_builder, success_embed_builder, normal_ember_builder
from main import InviteMonitor


class Invite(commands.Cog):
    """Manage invites"""

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

    async def catch_user(self, user_id: int):
        """効率よくユーザーデータを取得する"""
        if (user := self.bot.get_user(user_id)) is None:  # キャッシュから取得
            try:
                user = await self.bot.fetch_user(user_id)  # APIから取得
            except:
                user = "Unknown"  # 見つからない場合 'Unknown'
        return user

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        """招待が作成された際のイベント"""
        if target_channel := await self.bot.db.get_log_channel_id(invite.guild.id):  # サーバーで有効化されている場合
            if invite.guild.me.guild_permissions.manage_guild:  # 権限を確認
                # 招待キャッシュを更新
                await self.bot.update_server_cache(invite.guild)
                # ログを送信
                embed = discord.Embed(color=0xa8ffa8)
                embed.set_author(name="Invite Created", icon_url="https://cdn.discordapp.com/emojis/762303590365921280.png?v=1")
                embed.description = f"Invite [{invite.code}]({invite.url}) has been created by <@{invite.inviter.id}>\n\n"
                embed.description += f"`Channel  :`  <#{invite.channel.id}>\n"
                embed.description += f"`Max Uses :`  {self.parse_max_uses(invite.max_uses)} times\n"
                embed.description += f"`Max Age  :`  {self.parse_max_age(invite.max_age)}\n"
                embed.description += f"`Invite   :`  {invite.inviter}"
                await self.bot.get_channel(target_channel).send(embed=embed)
            else:  # 権限不足エラー
                pass  # TODO: manage_guild不足通知

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        """招待が削除された際のイベント"""
        if target_channel := await self.bot.db.get_log_channel_id(invite.guild.id):  # サーバーで有効化されている場合
            if invite.guild.me.guild_permissions.manage_guild:  # 権限を確認
                inviter = None
                if invite.code in self.bot.cache[invite.guild.id]:  # 招待キャッシュから、招待作成者を取得
                    inviter = self.bot.cache[invite.guild.id][invite.code]['author']
                # 招待キャッシュを更新
                await self.bot.update_server_cache(invite.guild)
                # ログを送信
                embed = discord.Embed(color=0xffbf7f)
                embed.set_author(name="Invite Deleted", icon_url="https://cdn.discordapp.com/emojis/762303590529892432.png?v=1")
                embed.description = f"Invite [{invite.code}]({invite.url}) by {'<@' + str(inviter) + '>' if inviter else 'Unknown'} has deleted or expired.\n\n"
                embed.description += f"`Channel  :`  <#{invite.channel.id}>\n"
                user = await self.catch_user(inviter)  # 招待者を取得
                embed.description += f"`Inviter  :`  {user}\n"
                await self.bot.get_channel(target_channel).send(embed=embed)
                # Triggerに登録されたコードが削除されていないかどうか確認する
                if invite.code in await self.bot.db.get_code_trigger_list(invite.guild.id):
                    # 通知文を送信
                    await self.bot.get_channel(target_channel).send(f":warning: Invite `{invite.code}` was deleted, so this trigger is no longer available!")
                    await self.bot.db.remove_code_trigger(invite.guild.id, invite.code)  # 削除する
            else:  # 権限不足エラー
                pass  # TODO: manage_guild不足通知

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """メンバーが参加した際のイベント"""
        if target_channel := await self.bot.db.get_log_channel_id(member.guild.id):  # サーバーで有効化されている場合
            if member.guild.me.guild_permissions.manage_guild:  # 権限を確認
                old_invite_cache = self.bot.cache[member.guild.id]  # 前の招待キャッシュを取得
                new_invite_cache = await self.bot.update_server_cache(member.guild)  # 後の招待キャッシュを取得
                res = await self.check_invite_diff(old_invite_cache, new_invite_cache)  # 差異から招待者を特定
                # ログを送信
                embed = discord.Embed(color=0xa8d3ff)
                embed.set_author(name="Member Joined", icon_url="https://cdn.discordapp.com/emojis/762305608271265852.png")
                embed.set_thumbnail(url=member.avatar_url)
                if res is not None:  # ユーザーが判別できた場合
                    # 招待作成者の招待履歴に記録
                    await self.bot.db.add_invited_to_inviter(member.guild.id, res[0], member.id)
                    # 招待された人の招待作成者を記録
                    await self.bot.db.add_inviter_to_invited(member.guild.id, res[0], member.id)
                    await self.bot.db.add_code_to_invited(member.guild.id, res[1], member.id)
                    inviter = await self.catch_user(res[0])  # 招待者を取得
                    # ログを送信
                    embed.description = f"<@{member.id}> has joined through [{res[1]}](https://discord.gg/{res[1]}) made by <@{inviter.id}>\n\n"
                    embed.description += f"`User    :`  {member}\n"
                    embed.description += f"`Code    :`  {res[1]}\n"
                    embed.description += f"`Inviter :`  {inviter}\n"
                else:
                    embed.description = f"<@{member.id}> has joined\n\n"
                    embed.description += f"`User    :`  {member}\n"
                    embed.description += f"`Inviter :`  Unknown\n"
                # 参加者のアカウント作成日時を経過した時間で表示
                embed.timestamp, delta = self.get_delta_time(member.created_at, with_warn=True)
                # ログを送信
                embed.description += f"`Created :` {delta} ago"
                embed.set_footer(text=f"{member.guild.name} | {len(member.guild.members)}members", icon_url=member.guild.icon_url)
                await self.bot.get_channel(target_channel).send(embed=embed)
                # UserTriggerを確認
                if res is None:  # 招待を認識できなかった場合
                    return
                elif member.guild.me.guild_permissions.manage_roles:  # ロール管理権限がある場合
                    if res[0] in await self.bot.db.get_user_trigger_list(member.guild.id):  # 招待者が設定されている場合
                        roles = await self.bot.db.get_user_trigger_roles(member.guild.id, res[0])
                        target_role = []
                        for role_id in roles:
                            if (role := member.guild.get_role(role_id)) is not None:
                                target_role.append(role)  # 役職を取得できた場合、追加
                        error_msg = ""
                        if not target_role:  # 役職を取得できない場合
                            await self.bot.get_channel(target_channel).send(f":warning: Roles were not found, so code trigger **{res[0]}** is no longer available!")
                            await self.bot.db.remove_user_trigger(member.guild.id, res[0])
                        else:
                            try:
                                await member.add_roles(*target_role)  # リスト内のロールオブジェクトをそれぞれ指定
                            except:  # 役職の付与に失敗した場合
                                error_msg += f":x: Failed to add role `{','.join([role.name for role in target_role])}` of user trigger **{res[0]}**\nPlease check position of role! These may be higher role than I have.\n"
                        if error_msg != "":  # エラーが発生した場合
                            await self.bot.get_channel(target_channel).send(error_msg)

                    elif res[1] in await self.bot.db.get_code_trigger_roles(member.guild.id, res[1]):
                        roles = await self.bot.db.get_code_trigger_roles(member.guild.id, res[1])
                        target_role = []
                        for role_id in roles:
                            if (role := member.guild.get_role(role_id)) is not None:
                                target_role.append(role)  # 役職を取得できた場合、追加
                        error_msg = ""
                        if not target_role:  # 役職を取得できない場合
                            await self.bot.get_channel(target_channel).send(f":warning: Roles were not found, so user trigger **{res[1]}** is no longer available!")
                            await self.bot.db.remove_code_trigger(member.guild.id, res[1])
                        else:
                            try:
                                await member.add_roles(*target_role)  # リストのロールオブジェクトをそれぞれ指定
                            except:  # 役職の付与に失敗した場合
                                error_msg += f":x: Failed to add role `{','.join([role.name for role in target_role])}` of code trigger **{res[1]}**\nPlease check position of role! These may be higher role than I have.\n"
                        if error_msg != "":  # エラーが発生した場合
                            await self.bot.get_channel(target_channel).send(error_msg)
            else:  # 権限不足エラー
                pass  # TODO: manage_guild不足通知

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """メンバーが退出した際のイベント"""
        if target_channel := await self.bot.db.get_log_channel_id(member.guild.id):  # サーバーで有効化されている場合
            if member.guild.me.guild_permissions.manage_guild:  # 権限を確認
                # ログを送信
                embed = discord.Embed(color=0xffa8a8)
                embed.set_author(name="Member Left", icon_url="https://cdn.discordapp.com/emojis/762305607625605140.png")
                embed.set_thumbnail(url=member.avatar_url)
                # メンバーがデータベース上に存在しないか、招待元がNoneの場合
                invite_from = await self.bot.db.get_user_invite_from(member.guild.id, member.id)
                if await self.bot.db.is_registered_user(member.guild.id, member.id) or invite_from:
                    embed.description = f"<@{member.id}> has left\n\n"
                    embed.description += f"`User    :`  {member}\n"
                    embed.description += f"`Inviter :`  Unknown\n"
                else:  # 招待者データがある場合
                    inviter_id = invite_from
                    invite_code = await self.bot.db.get_user_invite_code(member.guild.id, member.id)
                    inviter = await self.catch_user(inviter_id)
                    embed.description = f"<@{member.id}> invited by {'<@' + inviter.id + '>' if inviter != 'Unknown' else 'Unknown'} has left\n\n"
                    embed.description += f"`User    :`  {member}\n"
                    embed.description += f"`Code    :`  {invite_code}\n"
                    embed.description += f"`Inviter :`  {inviter}\n"
                # 滞在した時間を何時間経過したかで表示
                embed.timestamp, delta = self.get_delta_time(member.joined_at)
                embed.description += f"`Stayed  :`  {delta}"
                embed.set_footer(text=f"{member.guild.name} | {len(member.guild.members)}members", icon_url=member.guild.icon_url)
                await self.bot.get_channel(target_channel).send(embed=embed)

    @commands.Cog.listener()
    async def check_invite_diff(self, old_invites, new_invites):
        """
        招待キャッシュの差異から、招待者を取得
        :param old_invites: 前の招待キャッシュ
        :param new_invites: 後の招待キャッシュ
        :return: [招待者ID:int, 招待コード: str]
        """
        for invite in old_invites:
            if invite in new_invites:
                if old_invites[invite]["uses"] != new_invites[invite]["uses"]:  # 使用回数が変わっている場合
                    return [old_invites[invite]["author"], invite]
            else:
                return [old_invites[invite]["author"], invite]  # 招待コードがなくなっている場合→使用上限回数に達した場合
        else:
            return None  # 何らかの問題で,変更点が見つからなかった場合

    @commands.command(aliases=["inv"], usage="invite (@bot)", brief="Get bot's invite link", description="Show invite link of the bot. If some bot mentioned, send invite link of those.")
    async def invite(self, ctx):
        if not ctx.message.mentions:  # メンションがない場合、このBOTの招待リンクを表示
            embed = discord.Embed(title="Invite links", color=0xffa8ff)
            embed.description = "Here are some links. If you need help, please feel free to ask in Support Server. Thanks!"
            embed.set_thumbnail(url=self.bot.user.avatar_url)
            embed.add_field(name="Invite URL", value=self.bot.static_data.invite, inline=False)
            embed.add_field(name="Support Server", value=self.bot.static_data.server, inline=False)
            embed.add_field(name="Additional links", value=f"[Vote me on top.gg]({self.bot.static_data.top_gg}) | [Donate to keep online]({self.bot.static_data.donate})")
            embed.set_footer(text="Thank you for using InviteMonitor!", icon_url="https://cdn.discordapp.com/emojis/769855038964891688.png")
            await ctx.send(embed=embed)
        else:  # メンションがある場合、メンションされたBOTの招待リンクを表示
            embed = discord.Embed(title="Invite links", color=0xff7fff)
            count = 0
            for target_user in ctx.message.mentions:
                if count == 10:
                    break
                if target_user.bot:
                    embed.add_field(name=str(target_user), value=f"https://discord.com/oauth2/authorize?client_id={target_user.id}&scope=bot&permissions=-8", inline=False)
                else:  # BOTでない場合
                    embed.add_field(name=str(target_user), value=f"{target_user} is not the bot!", inline=False)
                count += 1
            await ctx.send(embed=embed)

    @identifier.is_has_manage_roles()
    @commands.group(usage="code_trigger", aliases=["ct"], brief="Auto role with used code", description="Manage triggers that give specific role to participant who joined with specific invite code.")
    @identifier.debugger
    async def code_trigger(self, ctx):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(title="Code Triggers")
            embed.description = "If someone join through [code], give [@role]\n`[index] : [code]`\n`[@role]`"
            count = 1
            for trigger_name in await self.bot.db.get_code_trigger_list(ctx.guild.id):
                roles = await self.bot.db.get_code_trigger_roles(ctx.guild.id, trigger_name)
                embed.add_field(name=f"`{count}       :`  {trigger_name}", value=" ".join([f"<@&{ctx.guild.get_role(role).id}>" for role in roles]), inline=False)
                count += 1
            if count == 1:
                ex_invite: str
                if ctx.guild.id in self.bot.cache and self.bot.cache[ctx.guild.id]:
                    ex_invite = list(self.bot.cache[ctx.guild.id].keys())[0]
                else:
                    ex_invite = "RbzSSrw"
                embed.description += f"\n\n**No triggers here! To get started:**\n{self.bot.PREFIX}code_trigger add [code] [roles]\n**For example:**\n{self.bot.PREFIX}code_trigger add {ex_invite} {ctx.guild.roles[-1].mention if ctx.guild.roles else '@new_role'}\n\n{self.bot.PREFIX}help code_trigger to learn more."
            embed.set_footer(text=f"Total {count - 1} code triggers in {ctx.guild.name}", icon_url=ctx.guild.icon_url)
            await ctx.send(embed=embed)

    @code_trigger.command(name="add", usage="user_trigger add [invite code] [@role]", description="Add new trigger. (If participant joined with [invite code], then give [@role])")
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def code_trigger_add(self, ctx, code, *, role):
        # 数を確認
        if await self.bot.db.get_code_trigger_count(ctx.guild.id) == 5:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(":x: You already have 5 triggers! Please delete trigger before make new one.")
        # 招待コードを取得
        target_code = re.sub(r"(https?://)?(www.)?(discord.gg|(ptb.|canary.)?discord(app)?.com/invite)/", "", code)
        if target_code not in self.bot.cache[ctx.guild.id]:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"{self.bot.static_data.emoji_no_mag} Invalid code was specified.")
        target_role = self.get_roles_from_string(role, ctx.guild)
        if not target_role:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"{self.bot.static_data.emoji_no_mag} Role not found. Please make sure that role exists.")
        elif len(target_role) > 5:
            return await ctx.send(":x: Too many roles! You can satisfy roles up to 5.")
        if target_code in await self.bot.db.get_code_trigger_list(ctx.guild.id):  # 既に設定されている場合は確認する
            await warning_embed_builder(ctx, f"Invite code **{code}** is already configured.\nDo you want to override previous setting?", title="Type 'yes' to continue.")
            if not await self.bot.confirm(ctx):
                return
        await self.bot.db.add_code_trigger(ctx.guild.id, target_code, target_role)
        await ctx.send(f"{self.bot.static_data.emoji_invite_add} Code trigger has created successfully!")

    @code_trigger.command(name="remove", usage="user_trigger remove [index]", description="Remove exist trigger.", aliases=["delete", "del"])
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def code_trigger_remove(self, ctx, index):
        count = await self.bot.db.get_code_trigger_count(ctx.guild.id)
        if count == 0:
            await error_embed_builder(ctx, "No code triggers here yet.")
        elif index.isdigit() and 1 <= int(index) <= count:
            key_list = await self.bot.db.get_code_trigger_list(ctx.guild.id)
            await self.bot.db.remove_code_trigger(ctx.guild.id, key_list[int(index) - 1])
            await success_embed_builder(ctx, f"Code trigger **{index}** has deleted successfully!")
        else:
            await error_embed_builder(ctx, f"Invalid index!\nIndexes are found on `{self.bot.PREFIX}code_trigger`")

    @identifier.is_has_manage_roles()
    @commands.group(usage="user_trigger", aliases=["ut"], brief="Auto role with inviter", description="Manage triggers that give specific roles to participant who invited by specific user.")
    async def user_trigger(self, ctx):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(title="User triggers")
            embed.description = f"If someone was invited by [user], give [@role]\n`[index] : [user]`\n`[@role]`"
            count = 1
            for trigger_name in await self.bot.db.get_user_trigger_list(ctx.guild.id):
                roles = await self.bot.db.get_user_trigger_roles(ctx.guild.id, trigger_name)
                embed.add_field(name=f"`{count}       :`  {trigger_name}", value=" ".join([f"<@&{ctx.guild.get_role(role).id}>" for role in roles]))
                count += 1
            if count == 1:
                embed.description += f"\n\n**No triggers here! To get started:**\n{self.bot.PREFIX}user_trigger add [user] [roles]\n**For example:**\n{self.bot.PREFIX}user_trigger add {self.bot.user.mention} {ctx.guild.roles[-1].mention if ctx.guild.roles else '@new_role'}\n\n{self.bot.PREFIX}help user_trigger to learn more."
            embed.set_footer(text=f"Total {count - 1} user triggers | {ctx.guild.name}", icon_url=ctx.guild.icon_url)
            await ctx.send(embed=embed)

    @user_trigger.command(name="add", usage="user_trigger add [@user] [@role]", description="Add new trigger. (If participant was invited by [@user], then give [@role])")
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def user_trigger_add(self, ctx, user, *, role):
        # 数を確認
        if len(await self.bot.db.get_user_trigger_count(ctx.guild.id)) == 5:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(":x: You already have 5 triggers! Please delete trigger before make new one.")
        # ユーザーを取得
        target_user = self.get_user_from_string(user, ctx.guild)
        if target_user is None:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"{self.bot.static_data.emoji_no_mag} User not found. Please make sure that user exists.")
        target_role = self.get_roles_from_string(role, ctx.guild)
        if not target_role:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"{self.bot.static_data.emoji_no_mag} Role not found. Please make sure that role exists.")
        elif len(target_role) > 5:
            return await ctx.send(":x: Too many roles! You can satisfy roles up to 5.")
        if target_user in await self.bot.db.get_user_trigger_roles(ctx.guild.id):  # 既に設定されている場合は確認する
            await warning_embed_builder(ctx, f"User **{user}** is already configured.\nDo you want to override previous setting?", title="Type 'yes' to continue.")
            if not await self.bot.confirm(ctx):
                return
        await self.bot.db.add_user_trigger(ctx.guild.id, target_user, target_role)
        await ctx.send(f"{self.bot.static_data.emoji_invite_add} User trigger has created successfully!")

    @user_trigger.command(name="remove", usage="user_trigger remove [index]", description="Delete exist trigger.", aliases=["delete", "del"])
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def user_trigger_remove(self, ctx, index):
        count = await self.bot.db.get_user_trigger_count(ctx.guild.id)
        if count == 0:
            await error_embed_builder(ctx, "No user triggers here yet.")
        elif index.isdigit() and 1 <= int(index) <= count:
            key_list = await self.bot.db.get_user_trigger_list(ctx.guild.id)
            await self.bot.db.remove_user_trigger(ctx.guild.id, key_list[int(index) - 1])
            await success_embed_builder(ctx, f"User trigger **{index}** has deleted successfully!")
        else:
            await error_embed_builder(ctx, f"Invalid index!\nIndexes are found on `{self.bot.PREFIX}user_trigger`")

    def get_user_from_string(self, user_string, guild):
        target_user: str
        user = None
        if (user_match := re.match(r"<@!?(\d+)>", user_string)) is not None:  # メンションの場合
            return user_match.group()
        elif user_string.isdigit() and ((user := discord.utils.get(guild.members, id=int(user_string))) is not None):
            return str(user.id)
        else:  # 名前で検索
            if (user := discord.utils.get(guild.members, name=user_string)) is not None:
                return str(user.id)
            else:  # 見つからなかった場合
                return None

    def get_roles_from_string(self, role_text, guild):
        role_texts = role_text.split()
        roles = []
        for role_string in role_texts:  # それぞれを確認していく
            target_user: str
            role = None
            if (user_match := re.match(r"<@&(\d+)>", role_string)) is not None:  # メンションの場合
                roles.append(int(user_match.group()))
            elif role_string.isdigit() and ((role := discord.utils.get(guild.roles, id=int(role_string))) is not None):
                roles.append(role.id)
            else:  # 名前で検索
                if (role := discord.utils.get(guild.roles, name=role_string)) is not None:
                    roles.append(role.id)
        return roles

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

    def get_delta_time(self, base_datetime, with_warn=False):
        now = datetime.datetime.now(datetime.timezone.utc)  # JST -> UTC
        delta = now - pytz.timezone('UTC').localize(base_datetime)  # native -> aware(UTC)
        if delta.days == 0:  # 一日以内場合
            delta = f"__**{delta.seconds // 3600}hours {(delta.seconds % 3600) // 60}minutes**__"
            if with_warn:
                delta = f"__**{delta}**__"
        elif delta.days <= 7:  # 一週間以内の場合
            delta = f"**{delta.days}days {delta.seconds // 3600}hours**"
            if with_warn:
                delta = f"**{delta}**"
        else:  # それ以上の場合
            delta = f"{delta.days // 30}months {delta.seconds % 30}days"
        return [now, delta]


def setup(bot):
    bot.add_cog(Invite(bot))
