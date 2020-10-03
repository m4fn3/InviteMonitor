from discord.ext import commands
import discord, os, logging

logging.basicConfig(level=logging.INFO)

class InvStat(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix, intents=intents)
        self.cache = {}

    # event
    async def on_ready(self):
        print(f"Logged in to [{self.user}]")

    async def on_invite_create(self, invite):
        if await self.check_permission(invite.guild):
            await self.get_channel(664376321278738453).send(f"invite create detected:{invite.code}")

    async def on_invite_delete(self, invite):
        if await self.check_permission(invite.guild):
            await self.get_channel(664376321278738453).send(f"invite delete detected:{invite.code}")

    async def on_guild_join(self, guild):
        if await self.check_permission(guild):
            await self.update_server_cache(guild)

    async def on_guild_remove(self, guild):
        await self.clear_server_cache(guild.id)

    # func
    async def update_server_cache(self, guild):
        invites = await guild.invites()

    async def clear_server_cache(self, guild_id):
        del self.cache[guild_id]

    async def update_all_server_cache(self, guilds):
        for guild in guilds:
            await self.update_server_cache(guild)

    async def check_permission(self, guild):
        if guild.me.guild_permissions.manage_guild:
            return 1
        else:
            for text_channel in guild.text_channels:
                if guild.me.permissions_in(text_channel).send_messages:
                    await text_channel.send("`manage_guild`権限が不足しています")
                    break
            else:
                try:
                    await guild.owner.send(f"`{guild.name}`サーバー内で`manage_guild`権限が不足しています")
                except:
                    pass
            return 0

    #TODO: on_invite_create, on_invite_delete の取得+処理は通知チャンネルが設定されてからに変更
    #TODO: データベースはログ送信先に登録されているチャンネルIDさーばーIDリストを保存
    #TODO: 招待コード,回数を文字列で保存,文字列の差異を取得して結果を確認する - (コード、回数)は文字数が決まっているので、異なるものが数字⇒OKだが、文字の場合、招待が削除されているので無視する,split+見つかったところの文字indexからコードを取得できる

if __name__ == '__main__':
    intents = discord.Intents.all()
    bot = InvStat(command_prefix="i=", intents=intents)
    bot.run(os.getenv("TOKEN"))
