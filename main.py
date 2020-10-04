from discord.ext import commands, tasks
import discord, os, logging, pickle

logging.basicConfig(level=logging.INFO)

class InvStat(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix, intents=intents)
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
        self.load_extension("invite")

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

    async def on_invite_create(self, invite: discord.Invite):
        if (target_channel := self.db[str(invite.guild.id)]["channel"]) is not None:
            if self.check_permission(invite.guild):
                await self.update_server_cache(invite.guild)
                embed = discord.Embed(title="Invite Created", color=0x00ff7f)
                embed.description = f"Invite [{invite.code}]({invite.url}) has been created by [{str(invite.inviter)}]({invite.url})"
                embed.add_field(name="Channel", value=f"<#{invite.channel.id}>")  # Object型になる可能性があるので
                embed.add_field(name="MaxUses", value=f"{invite.max_uses}")
                embed.add_field(name="MaxAge", value=f"{invite.max_age}")
                await bot.get_channel(target_channel).send(embed=embed)

    async def on_invite_delete(self, invite):
        if (target_channel := self.db[str(invite.guild.id)]["channel"]) is not None:
            if self.check_permission(invite.guild):
                inviter = None
                # キャッシュに存在しない場合を考慮して,場合分けする
                if invite.code in self.cache[str(invite.guild.id)]:
                    inviter = self.cache[str(invite.guild.id)][invite.code]['author']
                await self.update_server_cache(invite.guild)
                embed = discord.Embed(title="Invite Deleted", color=0xff8c00)
                embed.description = f"Invite [{invite.code}]({invite.url}) by [{await self.fetch_user(inviter) if inviter else 'Unknown'}]({invite.url}) has deleted or expired."
                embed.add_field(name="Channel", value=f"<#{invite.channel.id}>")  # Object型になる可能性があるので
                await bot.get_channel(target_channel).send(embed=embed)

    async def on_member_join(self, member: discord.Member):
        if (target_channel := self.db[str(member.guild.id)]["channel"]) is not None:
            if self.check_permission(member.guild):
                old_invite_cache = self.cache[str(member.guild.id)]
                new_invite_cache = await self.update_server_cache(member.guild)
                res = await self.check_invite_diff(old_invite_cache, new_invite_cache)
                embed = discord.Embed(title="Member Joined", color=0x00ffff)
                embed.set_thumbnail(url=member.avatar_url)
                if res is not None:  # ユーザーが判別できた場合
                    # 招待作成者の招待履歴に記録
                    if str(res[0]) not in self.db[str(member.guild.id)]["users"]:
                        self.db[str(member.guild.id)]["users"][str(res[0])] = {
                            "to_all": {member.id},
                            "to": {member.id},
                            "from": None
                        }
                    else:
                        self.db[str(member.guild.id)]["users"][str(res[0])]["to"].add(member.id)
                        self.db[str(member.guild.id)]["users"][str(res[0])]["to_all"].add(member.id)
                    # 招待された人の招待作成者を記録
                    if str(member.id) not in self.db[str(member.guild.id)]["users"]:
                        self.db[str(member.guild.id)]["users"][str(member.id)] = {
                            "to_all": set(),
                            "to": set(),
                            "from": res[0]
                        }
                    else:
                        self.db[str(member.guild.id)]["users"][str(member.id)]["from"] = res[0]
                    if (inviter := self.get_user(res[0])) is None:
                        try:
                            inviter = await self.fetch_user(res[0])
                        except:
                            inviter = "Unknown"
                    embed.description = f"[{member}](https://discord.gg/{res[1]}) has joined through [{res[1]}](https://discord.gg/{res[1]}) made by [{inviter}](https://discord.gg/{res[1]})"
                    embed.add_field(name="User", value=f"{member}")
                    embed.add_field(name="Invite", value=f"{res[1]} - {inviter}")
                else:
                    embed.description = f"[{member}](https://discord.com) has joined"
                    embed.add_field(name="User", value=f"{member}")
                    embed.add_field(name="Invite", value=f"Unknown")
                await bot.get_channel(target_channel).send(embed=embed)

    async def on_member_remove(self, member: discord.Member):
        if (target_channel := self.db[str(member.guild.id)]["channel"]) is not None:
            if self.check_permission(member.guild):
                embed = discord.Embed(title="Member Left", color=0xff1493)
                embed.set_thumbnail(url=member.avatar_url)
                if (str(member.id) not in self.db[str(member.guild.id)]["users"]) or (self.db[str(member.guild.id)]["users"][str(member.id)]["from"] is None):
                    embed.description = f"[{member}](https://discord.com) has left"
                    embed.add_field(name="User", value=f"{member}")
                    embed.add_field(name="Invite", value=f"Unknown")
                else:
                    inviter_id = self.db[str(member.guild.id)]["users"][str(member.id)]["from"]
                    if str(inviter_id) in self.db[str(member.guild.id)]["users"] and member.id in self.db[str(member.guild.id)]["users"][str(inviter_id)]["to"] and member.id in self.db[str(member.guild.id)]["users"][str(inviter_id)]["to_all"]:
                        self.db[str(member.guild.id)]["users"][str(inviter_id)]["to"].remove(member.id)
                    if (inviter := self.get_user(inviter_id)) is None:
                        try:
                            inviter = await self.fetch_user(inviter_id)
                        except:
                            inviter = "Unknown"
                    embed.description = f"[{member}](https://discord.com) invited by [{inviter}](https://discord.com) has left"
                    embed.add_field(name="User", value=f"{member}")
                    embed.add_field(name="Invite", value=f"{inviter}")
                await bot.get_channel(target_channel).send(embed=embed)

    async def check_invite_diff(self, old_invites, new_invites):
        for invite in old_invites:
            if invite in new_invites:
                if old_invites[invite] != new_invites[invite]:
                    return [old_invites[invite]["author"], invite]  # 使用回数が変わっている場合
            else:
                return [old_invites[invite]["author"], invite]  # 招待コードがなくなっている場合→使用上限回数に達した場合
        else:
            return None  # 何らかの問題で,変更点が見つからなかった場合

    async def on_guild_join(self, guild):
        if self.check_permission(guild):
            await self.update_server_cache(guild)
        self.register_server_data(guild.id)

    async def on_guild_remove(self, guild):
        self.clear_server(guild.id)

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

    def check_permission(self, guild):
        if guild.me.guild_permissions.manage_guild:
            return 1
        else:
            return 0

    #TODO: embed色付ける

    @tasks.loop(minutes=1)
    async def save_database(self):
        with open("database.pkl", "wb") as f:
            pickle.dump(self.db, f)

if __name__ == '__main__':
    intents = discord.Intents.all()
    bot = InvStat(command_prefix="i/", intents=intents)
    bot.run(os.getenv("TOKEN"))
