from discord.ext import commands, tasks
import discord, os, logging, pickle, time
from help import Help

logging.basicConfig(level=logging.INFO)

PREFIX = "i/"
PREFIXES = "i/"

class InvStat(commands.Bot):
    def __init__(self, command_prefix, help_command, intents, status, activity):
        super().__init__(command_prefix, help_command, intents=intents, status=status, activity=activity)
        self.PREFIX = PREFIX
        self.datas = {
            "invite": "https://discord.com/oauth2/authorize?client_id=761820118379921440&scope=bot&permissions=-8",
            "server": "https://discord.gg/RbzSSrw",
            "author": 513136168112750593,
            "emojis": {
                "loading": "<a:loading:762566694572916766>",
                "invite_add": "<:invite_add:762303590365921280>",
                "invite_del": "<:invite_del:762303590529892432>",
                "member_join": "<:member_join:762305608271265852>",
                "member_leave": "<:member_leave:762305607625605140>"
            }
        }
        with open("database.pkl", "rb") as db:
            self.db = pickle.load(db)
        self.cache = {}
        # db = {
        #     "server-id": {
        #         "channel": None,
        #         "users": {
        #             "id": {
        #                 "invites": {},
        #                 "invited_by": 113131
        #             }
        #         }
        #     }
        # }
        self.bot_cogs = ["developer", "invite", "setting", "manage"]
        for cog in self.bot_cogs:
            self.load_extension(cog)
        self.uptime = time.time()

    async def on_ready(self):
        print(f"Logged in to [{self.user}]")
        # 既に開始していなければデータベース自動保存を有効にする
        if not self.save_database.is_running():
            self.save_database.start()
        # データベース内にないサーバーの情報を補完
        prepare_list = [guild.id for guild in self.guilds if str(guild.id) not in self.db]
        for guild_id in prepare_list:
            self.register_server_data(guild_id)
        # 全サーバーの招待コード&使用済回数情報を取得
        await self.update_all_server_cache(self.guilds)
        await self.change_presence(status=discord.Status.online, activity=discord.Game(f"{self.PREFIX}help | {len(self.guilds)}servers\n"))

    async def on_guild_join(self, guild):
        if self.check_permission(guild.me):
            await self.update_server_cache(guild)
        self.register_server_data(guild.id)

    async def on_guild_remove(self, guild):
        self.clear_server(guild.id)

    async def on_message(self, message):
        if message.content == f"<@!{self.user.id}>":
            return await message.channel.send(f"My prefix is **{self.PREFIX}**\nSee list of commands by `{self.PREFIX}help`")
        else:
            await self.process_commands(message)

    def register_server_data(self, guild_id):
        # データベースにサーバー情報を追加
        self.db[str(guild_id)] = {
            "channel": None,
            "users": {}
        }

    def clear_server(self, guild_id):
        # データベース,キャッシュからサーバーのデータを削除
        del self.db[str(guild_id)]
        del self.cache[guild_id]

    async def update_server_cache(self, guild):
        # サーバーの招待情報のキャッシュを更新
        invites = await guild.invites()
        invite_dict = {}
        for invite in invites:
            invite_dict[invite.code] = {
                "uses": invite.uses,
                "author": invite.inviter.id
            }
        self.cache[str(guild.id)] = invite_dict
        return invite_dict

    async def update_all_server_cache(self, guilds):
        # 全てのサーバーの招待情報のキャッシュを更新
        for guild in guilds:
            if self.db[str(guild.id)]["channel"] is not None:
                await self.update_server_cache(guild)

    def check_permission(self, member):
        if member.guild_permissions.manage_guild:
            return 1
        else:
            return 0

    @tasks.loop(minutes=1)
    async def save_database(self):
        with open("database.pkl", "wb") as f:
            pickle.dump(self.db, f)

if __name__ == '__main__':
    intents = discord.Intents.all()
    bot = InvStat(command_prefix=commands.when_mentioned_or(PREFIXES), help_command=Help(),intents=intents, status=discord.Status.dnd, activity=discord.Game("Starting...\n"))
    bot.run(os.getenv("TOKEN"))
