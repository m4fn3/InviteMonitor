import asyncpg
import discord
import logging
import os
import time
from discord.ext import commands, tasks
from dotenv import load_dotenv

from help import Help

# 環境変数の読み込み
load_dotenv(verbose=True)
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# ログの設定
logging.basicConfig(level=logging.INFO)

# PREFIX
PREFIX = "i/"
PREFIXES = "i/"


class InviteMonitor(commands.Bot):
    def __init__(self, command_prefix, help_command, intents, status, activity):
        super().__init__(command_prefix, help_command, intents=intents, status=status, activity=activity)
        self.PREFIX = PREFIX
        # TODO: namedtuple=イミュータブルに変更 - datasは英語的に問題があるので変更
        self.datas = {
            "invite": "https://discord.com/oauth2/authorize?client_id=761820118379921440&scope=bot&permissions=-8",
            "server": "https://discord.gg/RbzSSrw",
            "author": 513136168112750593,
            "emojis": {
                "loading": "<a:loading:762566694572916766>",
                "invite_add": "<:invite_add:762303590365921280>",
                "invite_del": "<:invite_del:762303590529892432>",
                "member_join": "<:member_join:762305608271265852>",
                "member_leave": "<:member_leave:762305607625605140>",
                "no_mag": "<:no_mag:763683888236986388>"
            }
        }
        self.db = await asyncpg.connect(os.getenv("DATABASE_URL"))
        self.cache = {}
        self.bot_cogs = ["developer", "invite", "setting", "manage", "cache"]
        for cog in self.bot_cogs:
            self.load_extension(cog)  # Cogの読み込み
        self.uptime = time.time()  # 起動時刻を取得

    async def on_ready(self):
        print(f"Logged in to [{self.user}]")
        # データベース内に登録されていないサーバーの、サーバー情報をデータベースに追加
        for guild in self.guilds:
            if guild.id not in self.db:  # TODO: db対応が必要
                self.register_server(guild.id)
        # 全てのサーバーの招待情報のキャッシュを更新 # NOTE: ダウンタイムにサーバーを退出したと考えると、データベース上のサーバーリストとの照会も必要かもしれない
        for guild in self.guilds:
            if self.db[str(guild.id)]["channel"] is not None:  # TODO: データベースにあるかどうかの判定をデータベースに対応
                await self.update_server_cache(guild)
        # 起動後のBOTステータスを設定
        await self.change_presence(status=discord.Status.online, activity=discord.Game(f"{self.PREFIX}help | {len(self.guilds)}servers\n"))

    async def on_guild_join(self, guild):
        # サーバー情報をデータベースに追加
        self.register_server(guild.id)

    async def on_guild_remove(self, guild):
        # サーバー情報&招待キャッシュを削除
        del self.db[str(guild.id)]  # TODO: DB対応
        if guild.id in self.cache:
            del self.cache[guild.id]

    async def on_message(self, message):
        if message.content == f"<@!{self.user.id}>":  # メンションされた場合、簡単な説明分を送信
            return await message.channel.send(f"My prefix is **{self.PREFIX}**\nSee list of commands by `{self.PREFIX}help`")
        else:  # コマンドを処理
            await self.process_commands(message)

    def register_server(self, guild_id):
        # TODO: DBに対応 - データベースにサーバー情報を追加
        self.db[str(guild_id)] = {
            "channel": None,
            "users": {},
            "roles": {
                "code": {},
                "user": {}
            }
        }

    async def update_server_cache(self, guild):
        # サーバーの招待キャッシュを更新
        invites = {invite.code: {"uses": invite.uses, "author": invite.inviter.id} for invite in await guild.invites()}
        self.cache[str(guild.id)] = invites
        return invites

    def check_permission(self, member):
        # TODO: 別のクラスとして用意するか、それぞれの部分で逐一書く
        if member.guild_permissions.manage_guild:
            return 1
        else:
            return 0


if __name__ == '__main__':
    bot_intents = discord.Intents.all()  # 全てのインテントを有効化
    bot = InviteMonitor(command_prefix=commands.when_mentioned_or(PREFIXES), help_command=Help(), intents=bot_intents, status=discord.Status.dnd, activity=discord.Game("Starting...\n"))
    bot.run(os.getenv("TOKEN"))  # BOTを起動
