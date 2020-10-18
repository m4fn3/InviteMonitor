import asyncpg
import discord
import logging
import os
import time
import json
from discord.ext import commands, tasks
from dotenv import load_dotenv

from help import Help
from SQLManager import SQLManager

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
        self.uptime = time.time()  # 起動時刻を取得
        self.PREFIX = PREFIX
        self.bot_cogs = ["developer", "invite", "setting", "manage", "cache"]

        with open("./static_data.json") as f:  # 固定データを読み込み
            self.static_data = json.load(f)

        # データベース接続準備
        self.db = SQLManager(os.getenv("DATABASE_URL"))
        self.cache = {}  # 招待キャッシュ

        for cog in self.bot_cogs:
            self.load_extension(cog)  # Cogの読み込み

    async def on_ready(self):
        """キャッシュの準備ができた際のイベント"""
        print(f"Logged in to [{self.user}]")
        if not self.db.is_connected():  # データベースに接続しているか確認
            await self.db.connect()  # データベースに接続
        # 全てのサーバーの招待情報のキャッシュを更新
        for guild in await self.db.get_enabled_guild_ids():  # 有効化されているサーバーを取得
            await self.update_server_cache(guild)
        # 起動後のBOTステータスを設定
        await self.change_presence(status=discord.Status.online, activity=discord.Game(f"{self.PREFIX}help | {len(self.guilds)}servers\n"))

    async def on_guild_join(self, guild: discord.guild):
        """BOT自身がサーバーに参加した際のイベント"""
        # サーバー情報をデータベースに新規登録
        await self.db.register_new_guild(guild.id)

    async def on_guild_remove(self, guild):
        """BOT自身がサーバーを退出した際のイベント"""
        # 招待キャッシュを削除
        if guild.id in self.cache:
            del self.cache[guild.id]

    async def on_message(self, message):
        """メッセージを受け取った際のイベント"""
        if message.content == f"<@!{self.user.id}>":  # メンションされた場合、簡単な説明分を送信
            return await message.channel.send(f"My prefix is **{self.PREFIX}**\nSee list of commands by `{self.PREFIX}help`")
        else:  # コマンドを処理
            await self.process_commands(message)

    async def update_server_cache(self, guild: discord.guild):
        """サーバーの招待キャッシュを更新"""
        invites = {invite.code: {"uses": invite.uses, "author": invite.inviter.id} for invite in await guild.invites()}
        self.cache[guild.id] = invites
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
