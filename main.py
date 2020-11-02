import asyncio
import identifier
import logging
import os
import platform
import random
import time
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

from SQLManager import SQLManager
from help import Help
from identifier import error_embed_builder, success_embed_builder, normal_ember_builder
from static_data import StaticData

# 環境変数の読み込み
load_dotenv(verbose=True)
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# ログの設定
logging.basicConfig(level=logging.INFO)

# PREFIX
PREFIX = "i/"
PREFIXES = ["i/"]

if platform.system() == "Windows":  # テスト環境
    PREFIXES.append("i!")


class InviteMonitor(commands.Bot):
    def __init__(self, command_prefix, help_command, intents, status, activity):
        super().__init__(command_prefix, help_command, intents=intents, status=status, activity=activity)
        self.uptime = time.time()  # 起動時刻を取得
        self.PREFIX = PREFIX
        self.bot_cogs = ["developer", "invite", "setting", "manage", "cache"]

        self.static_data = StaticData()

        # データベース接続準備
        self.db = SQLManager(os.getenv("DATABASE_URL"), self.loop)
        self.cache = {}  # 招待キャッシュ

        for cog in self.bot_cogs:
            self.load_extension(cog)  # Cogの読み込み

    async def on_ready(self):
        """キャッシュの準備ができた際のイベント"""
        if not self.db.is_connected():  # データベースに接続しているか確認
            print(f"Logged in to [{self.user}]")
            await self.db.connect()  # データベースに接続
            # 全てのサーバーの招待情報のキャッシュを更新
            for guild_id in await self.db.get_enabled_guild_ids():  # 有効化されているサーバーを取得
                guild = self.get_guild(guild_id)
                if guild is None:  # BOTのダウンタイム中にサーバーを退出した場合
                    await self.db.disable_guild(guild_id)
                else:
                    await self.update_server_cache(guild)
            # サーバーを確認
            registered_guilds = set(await self.db.get_guild_ids())
            joined_guilds = {guild.id for guild in bot.guilds}
            new_guilds = joined_guilds - registered_guilds
            for guild in new_guilds:
                await self.db.register_new_guild(guild)
            # 起動後のBOTステータスを設定
            await self.change_presence(status=discord.Status.online, activity=discord.Game(f"{self.PREFIX}help | {len(self.guilds)}servers\n"))

    async def on_guild_join(self, guild: discord.guild):
        """BOT自身がサーバーに参加した際のイベント"""
        # サーバー情報をデータベースに新規登録
        await self.db.register_new_guild(guild.id)
        # 参加時メッセージを送信
        embed = discord.Embed(title="Thank you for inviteing me!", color=0xff7f7f)
        embed.description = f"To get started, simply type `{self.PREFIX}enable #channel`\nSince then monitor logs will be sent to the channel!\n\nIf you need help, please contact on [Support Server]({bot.static_data.server})"
        embed.set_footer(icon_url="https://cdn.discordapp.com/emojis/769855038964891688.png", text="I hope you will enjoy the bot:)")
        await self.find_send(guild, embed=embed)

    async def on_guild_remove(self, guild):
        """BOT自身がサーバーを退出した際のイベント"""
        # 招待キャッシュを削除
        await self.db.disable_guild(guild.id)
        if guild.id in self.cache:
            del self.cache[guild.id]

    async def on_message(self, message):
        """メッセージを受け取った際のイベント"""
        if message.content == f"<@!{self.user.id}>":  # メンションされた場合、簡単な説明分を送信
            await normal_ember_builder(message.channel, f"My prefix is **{self.PREFIX}**\nSee list of commands by `{self.PREFIX}help`")
        elif not self.is_ready():  # 準備ができるまでは待機
            return
        else:  # コマンドを処理
            await self.process_commands(message)

    async def update_server_cache(self, guild: discord.guild):
        """サーバーの招待キャッシュを更新"""
        if not (guild.me.guild_permissions.manage_guild and guild.me.guild_permissions.manage_channels):
            return await self.perm_lack_reporter(guild, ["manage_guild", "manage_channels"])
        invites = {invite.code: {"uses": invite.uses, "author": invite.inviter.id} for invite in await guild.invites()}
        self.cache[guild.id] = invites
        return invites

    async def confirm(self, ctx):
        """本当に実行するかの確認"""

        def check(m):
            return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

        try:
            msg = await self.wait_for('message', check=check, timeout=30)
            if msg.content not in ["yes", "y", "'yes'", "ok"]:
                await success_embed_builder(ctx, "Canceled!")
                return 0
        except asyncio.TimeoutError:
            await error_embed_builder(ctx, "Canceled because of no reply.")
            return 0
        else:
            return 1

    @identifier.debugger
    async def find_send(self, guild: discord.Guild, content: str = "", embed: Optional[discord.Embed] = None, try_owner: bool = False):
        args = {}
        if embed is not None:
            args["embed"] = embed
        if content != "":
            args["content"] = content
        channels = guild.text_channels
        random.shuffle(channels)
        if (sys_ch := guild.system_channel) is not None:
            channels.insert(0, sys_ch)
        for channel in channels:
            perms = channel.permissions_for(guild.me)
            if perms.send_messages and perms.embed_links and perms.read_messages:
                await channel.send(**args)
                break
        else:  # どのチャンネルにも送信できなかった場合
            if try_owner:
                try:
                    guild.owner.senr(**args)
                except:
                    pass

    @identifier.debugger
    async def perm_lack_reporter(self, guild: discord.Guild, perms: list):
        """権限不足通知を送信"""
        perm_str = "\n".join(["- " + perm for perm in perms])
        embed = discord.Embed(title=f"{self.static_data.emoji_stop}  Important Warning  {self.static_data.emoji_stop}", color=0xff0000)
        embed.description = "The feature was automatically __disabled__ because monitoring failed due to lack of following permission:" \
                            f"```diff\n{perm_str}```" \
                            f"If you want to continue monitoring, add permissions to the BOT and setup by `{self.PREFIX}enable` again."
        await self.log_send(guild, embed=embed)
        await self.db.disable_guild(guild.id)

    @identifier.debugger
    async def log_send(self, guild: discord.Guild, content: str = "", embed: Optional[discord.Embed] = None):
        """ログチャンネルにログめっせーぞを送信"""
        log_channel_id = await self.db.get_log_channel_id(guild.id)
        log_channel = self.get_channel(log_channel_id)
        if log_channel is None:
            embed = discord.Embed(title=f"{self.static_data.emoji_stop}  Important Warning  {self.static_data.emoji_stop}", color=0xff0000)
            embed.description = f"The feature was automatically __disabled__ because log channel (<#{log_channel_id}>) was not found\n" \
                                f"If you want to continue monitoring, setup different channel by `{self.PREFIX}enable` again."
            await self.db.disable_guild(guild.id)
            return await self.find_send(guild, embed=embed)
        perms = log_channel.permissions_for(guild.me)
        if not (perms.send_messages and perms.embed_links and perms.read_messages):
            embed = discord.Embed(title=f"{self.static_data.emoji_stop}  Important Warning  {self.static_data.emoji_stop}", color=0xff0000)
            embed.description = f"The feature was automatically __disabled__ because missing following permissions in log channel (<#{log_channel_id}>)" \
                                "```diff\n- read_messages\n- send_messages\n- embed_links```" \
                                f"If you want to continue monitoring, add permissions to the BOT and setup by `{self.PREFIX}enable` again."
            await self.db.disable_guild(guild.id)
            return await self.find_send(guild, embed=embed)
        args = {}
        if embed is not None:
            args["embed"] = embed
        if content != "":
            args["content"] = content
        await log_channel.send(**args)


if __name__ == '__main__':
    bot_intents = discord.Intents.all()  # 全てのインテントを有効化
    bot = InviteMonitor(command_prefix=PREFIXES, help_command=Help(), intents=bot_intents, status=discord.Status.dnd, activity=discord.Game("Starting...\n"))
    bot.run(os.getenv("TOKEN"))  # BOTを起動
