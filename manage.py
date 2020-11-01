import re
from typing import List, Tuple, Union

import discord
from discord.ext import commands

import identifier
from identifier import error_embed_builder, success_embed_builder, warning_embed_builder
from main import InviteMonitor


class Manage(commands.Cog):
    """Manage members"""

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

    # TODO: 適切なクールダウン設定

    def extract_user(self, condition):
        user_list = []
        for cond in condition.split():
            if (match := re.match(r"<@!?(?P<id>\d+)>", cond)) is not None:
                user_list.append(int(match.group("id")))
            elif cond.isdigit():
                user_list.append(int(cond))
            elif "#" in cond:
                if (user := discord.utils.get(self.bot.users, name=cond.split("#")[0], discriminator=cond.split("#")[1])) is not None:
                    user_list.append(user.id)
            else:
                if (user := discord.utils.get(self.bot.users, name=cond)) is not None:
                    user_list.append(user.id)
        return user_list

    @identifier.is_has_kick_members()
    @commands.command(usage="kick [@user]", brief="Kick and wipe their invite", description="Kick the mentioned user and delete invites made by that user.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def kick(self, ctx, *, condition):
        error_log = ""
        target_users = set()
        for target in self.extract_user(condition):
            if (member := ctx.guild.get_member(target)) is None:
                error_log += f"User not in this server: <@{target}>\n"
                continue
            try:
                await member.kick()
            except:
                error_log += f"Failed to kick user <@{target}>\n"
            else:
                target_users.add(str(target))
        if error_log != "":
            await error_embed_builder(ctx, error_log[:1900].rsplit("\n", 1)[0] + "\n..." if len(error_log) >= 1900 else error_log)
        if not target_users:
            return await error_embed_builder(ctx, "No user found to kick")
        for invite in await ctx.guild.invites():
            if str(invite.inviter.id) in target_users:
                await invite.delete()
        mentions_text = "<@" + "> <@".join(target_users) + ">"
        await success_embed_builder(ctx, f"{mentions_text[:1900].rsplit('<', 1)[0] + '...' if len(mentions_text) >= 1900 else mentions_text} has kicked successfully!")

    @identifier.is_has_ban_members()
    @commands.command(usage="ban [@user]", brief="Ban and wipe their invite", description="Ban the mentioned user and delete invites made by that user.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def ban(self, ctx, *, condition):
        error_log = ""
        target_users = set()
        for target in self.extract_user(condition):
            if (member := ctx.guild.get_member(target)) is None:
                error_log += f"User not in this server: <@{target}>\n"
                continue
            try:
                await member.ban()
            except:
                error_log += f"Failed to ban user <@{target}>\n"
            else:
                target_users.add(str(target))
        if error_log != "":
            await error_embed_builder(ctx, error_log[:1900].rsplit("\n", 1)[0] + "\n..." if len(error_log) >= 1900 else error_log)
        if not target_users:
            return await error_embed_builder(ctx, "No user found to ban")
        for invite in await ctx.guild.invites():
            if str(invite.inviter.id) in target_users:
                await invite.delete()
        mentions_text = "<@" + "> <@".join(target_users) + ">"
        await success_embed_builder(ctx, f"{mentions_text[:1900].rsplit('<', 1)[0] + '...' if len(mentions_text) >= 1900 else mentions_text} has banned successfully!")

    @identifier.is_has_kick_members()
    @commands.command(usage="kick_with [@user | invite code]", brief="Kick with inviter or code", description="Kick the members who was invited by specified user or invite code. Also delete invites made by them.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def kick_with(self, ctx, *, cond):
        # そのサーバーでログが設定されているか確認
        if not await self.bot.db.is_enabled_guild(ctx.guild.id):
            return await error_embed_builder(ctx, f"Monitoring not enabled! Please setup by `{self.bot.PREFIX}enable` command before this feature.")
        users, codes, wrongs, code_authors = await self.extract_condition(cond, ctx.guild)
        if wrongs:  # ワーニングが存在した場合
            await warning_embed_builder(ctx, "Invite code is invalid or the user does not exist on the server. " + ",".join(wrongs) + "\n")
        if not users and not codes:  # 条件が0の場合SQLでエラーになるので回避
            return await error_embed_builder(ctx, "No target found.")
        target_users = await self.bot.db.filter_with_code_and_from(codes, users, ctx.guild.id)
        target_users = target_users.union(set(code_authors))  # 招待コードの作者を追加
        target_users = target_users.union(set([int(user) for user in users]))  # 指定されたユーザーを追加(intに変換)
        error_log = ""
        # Kickに成功した人のみのリストを作成
        target_checked = set()
        for target in target_users:
            if (member := ctx.guild.get_member(target)) is None:
                continue  # サーバーに存在しない場合
            try:
                await member.kick()
            except:
                error_log += f"Failed to kick user <@{target}>\n"
            else:
                target_checked.add(str(target))
        if error_log != "":
            error_log += "They has same or higher role than me."
            await error_embed_builder(ctx, error_log[:1900].rsplit("\n", 1)[0] + "\n..." if len(error_log) >= 1900 else error_log)
        if not target_checked:
            return await error_embed_builder(ctx, f"No user found to kick.")
        for invite in await ctx.guild.invites():
            if (str(invite.inviter.id) in target_checked) or (invite.code in codes):
                await invite.delete()
        mentions_text = "<@" + "> <@".join(target_checked) + ">"
        await success_embed_builder(ctx, f"{mentions_text[:1900].rsplit('<', 1)[0] + '...' if len(mentions_text) >= 1900 else mentions_text} has kicked successfully!")

    @identifier.is_has_ban_members()
    @commands.command(usage="ban_with [@user | code]", brief="Ban with inviter or code", description="Ban the members who was invited by specified user or invite code. Also delete invites made by them.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def ban_with(self, ctx, *, cond):
        # そのサーバーでログが設定されているか確認
        if not await self.bot.db.is_enabled_guild(ctx.guild.id):
            return await error_embed_builder(ctx, f"Monitoring not enabled! Please setup by `{self.bot.PREFIX}enable` command before this feature.")
        users, codes, wrongs, code_authors = await self.extract_condition(cond, ctx.guild)
        if wrongs:  # ワーニングが存在した場合
            await warning_embed_builder(ctx, "Invite code is invalid or the user does not exist on the server. " + ",".join(wrongs) + "\n")
        if not users and not codes:  # 条件が0の場合SQLでエラーになるので回避
            return await error_embed_builder(ctx, "No target found.")
        target_users = await self.bot.db.filter_with_code_and_from(codes, users, ctx.guild.id)
        target_users = target_users.union(set(code_authors))  # 招待コードの作者を追加
        target_users = target_users.union(set([int(user) for user in users]))  # 指定されたユーザーを追加(intに変換)
        error_log = ""
        # Kickに成功した人のみのリストを作成
        target_checked = set()
        for target in target_users:
            if (member := ctx.guild.get_member(target)) is None:
                continue  # サーバーに存在しない場合
            try:
                await member.ban()
            except:
                error_log += f"Failed to ban user <@{target}>\n"
            else:
                target_checked.add(str(target))
        if error_log != "":
            error_log += "They has same or higher role than me."
            await error_embed_builder(ctx, error_log[:1900].rsplit("\n", 1)[0] + "\n..." if len(error_log) >= 1900 else error_log)
        if not target_checked:
            return await error_embed_builder(ctx, f"No user found to kick.")
        for invite in await ctx.guild.invites():
            if (str(invite.inviter.id) in target_checked) or (invite.code in codes):
                await invite.delete()
        mentions_text = "<@" + "> <@".join(target_checked) + ">"
        await success_embed_builder(ctx, f"{mentions_text[:1900].rsplit('<', 1)[0] + '...' if len(mentions_text) >= 1900 else mentions_text} has banned successfully!")

    async def extract_condition(self, condition: str, guild: discord.Guild) -> (List[discord.User], List[str], List[str]):
        user_list: List[Union[Tuple[int, str], Tuple[int]]] = []  # 抽出されたユーザーIDリスト
        code_list: List[Tuple[str, str]] = []  # 抽出された招待コードリスト
        users: List[str] = []  # 確認後のユーザーオブジェクトリスト
        codes: List[str] = []  # 確認後の招待コードリスト
        wrongs: List[str] = []  # 問題のある条件リスト
        code_authors: List[int] = []
        # (ユーザーIDまたｈ招待コード, 元条件)
        for cond in condition.split():
            # 形式を判定して仮リストに追加
            if (match := re.match(r"<@!?(?P<id>\d+)>", cond)) is not None:  # <!@>の形なら->間の数字を取得(ユーザー)
                user_list.append((int(match.group("id")), cond))
            elif (match := re.search(r"(https?://)?(www.)?(discord.gg|(ptb.|canary.)?discord(app)?.com/invite)/(?P<invite>[a-zA-Z_]{2,32})", cond)) is not None:  # https://discord.gg/の形なら->最後の文字列を取得(招待)
                code_list.append((match.group("invite"), cond))
            elif cond.isdigit():  # 全部数字なら->数字を取得(ユーザー)
                user_list.append((int(cond), cond))
            elif "#" in cond:  # #が含まれるなら->name#suuziを取得(ユーザー)
                if (user := discord.utils.get(self.bot.users, name=cond.split("#")[0], discriminator=cond.split("#")[1])) is not None:
                    user_list.append((user.id, cond))  # ユーザーが見つかった場合
                else:  # ユーザーが見つからなかった場合
                    wrongs.append(cond)
            else:  # 文字列を取得(招待)
                code_list.append((cond, cond))
        # 招待コードリストの確認
        for code_cond in code_list:  # 招待コードの確認
            if code_cond[0] not in self.bot.cache[guild.id]:  # 招待キャッシュに存在しない場合
                wrongs.append(code_cond[1])
            else:
                code_authors.append(self.bot.cache[guild.id][code_cond[0]]["author"])  # 招待の作成者を追加
            codes.append(code_cond[0])
        # ユーザーIDリストの確認
        for user_cond in user_list:
            if discord.utils.get(guild.members, id=user_cond[0]) is None:  # メンバーでない場合
                if len(user_cond) == 2:
                    wrongs.append(user_cond[1])
            users.append(str(user_cond[0]))

        return users, codes, wrongs, code_authors

    async def catch_user(self, user_id: int):
        """効率よくユーザーデータを取得する"""
        if (user := self.bot.get_user(user_id)) is None:  # キャッシュから取得
            try:
                user = await self.bot.fetch_user(user_id)  # APIから取得
            except:
                return None
        return user


def setup(bot):
    bot.add_cog(Manage(bot))
