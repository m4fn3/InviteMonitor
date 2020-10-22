import asyncpg
import json
import traceback2


class SQLManager:
    def __init__(self, database_url: str):
        self.con = None
        self.database_url = database_url

    async def connect(self) -> asyncpg.connection:
        """データベースに接続"""
        self.con = await asyncpg.connect(self.database_url)

    def is_connected(self) -> bool:
        """データベースに接続しているか確認"""
        if self.con is None:
            return False
        else:
            return True

    async def get_guild_ids(self) -> list:
        """登録されているサーバーIDのリストを取得"""
        # SELECT array_agg(id) FROM server // id列の値をすべて配列にして表示
        res = await self.con.fetchrow("SELECT array_agg(id) FROM server;")
        return dict(res)["array_agg"]

    async def is_enabled_guild(self, guild_id: int) -> bool:
        """特定のサーバーでモニターが有効になっているかどうかを確認"""
        # SELECT count(*) FROM server // そのような行の数を数えるidはprimary keyなので有効であるならば1,無効ならば0
        # WHERE channel is not null and id = $1 // channelがnullでない(=有効であり)かつidがguild_idであるものに適用
        res = await self.con.fetchrow("SELECT count(*) FROM server WHERE channel is not null and id = $1;", guild_id)
        return bool(res)  # 0,1を真偽値に変換

    async def register_new_guild(self, guild_id: int) -> None:
        """新規サーバーのデータを追加"""
        await self.con.execute("INSERT INTO server values($1)", guild_id)

    async def get_enabled_guild_ids(self) -> list:
        """登録されているサーバーIDのリストを取得"""
        # SELECT array_agg(id) FROM server WHERE channel is not null // channelがnullでない(=有効化されている)サーバーのidを配列で取得
        res = await self.con.fetchrow("SELECT array_agg(id) FROM server WHERE channel is not null;")
        if guild_ids := dict(res)["array_agg"]:  # データが存在する場合
            return guild_ids
        else:  # データが空の場合
            return []

    async def get_log_channel_id(self, guild_id: int) -> int:
        """ログ送信用チャンネルを取得"""
        res = await self.con.fetchrow("SELECT channel FROM server WHERE id = $1", guild_id)
        if res is None or res["channel"] is None:
            return None
        else:
            return res["channel"]

    async def get_code_trigger_list(self, guild_id: int) -> list:
        """招待コードトリガーに設定されているコードのリストを取得"""
        # SELECT array_agg(keys) FROM () r // keysを配列に整形して表示 (名前をつけないといけないため任意の名前r(AS r)を追加)
        # SELECT jsonb_object_keys(code_trigger) AS keys FROM server WHERE id = $1 // code_triggerのキー一覧を取得してkeysという名前で保存
        res = await self.con.fetchrow("""
            SELECT array_agg(keys) FROM (
                SELECT jsonb_object_keys(code_trigger) AS keys FROM server WHERE id = $1
            ) r
        """, guild_id)
        if res is None or res["array_agg"] is None:
            return []
        else:
            return res["array_agg"]

    async def get_code_trigger_count(self, guild_id: int) -> int:
        """招待コードトリガーの数を取得"""
        res = await self.con.fetchrow("select count(keys) from (select jsonb_object_keys(code_trigger) as keys from server where id = $1)r ;", guild_id)
        if res is None or res["count"]:
            return 0
        else:
            return res["count"]

    async def get_code_trigger_roles(self, guild_id: int, code: str) -> list:
        """招待コードトリガーに設定されている役職のリストを取得"""
        res = await self.con.fetchrow("SELECT code_trigger->>$1 AS f FROM server WHERE id = $2;", code, guild_id)
        if res is None or res["f"] is None:
            return []
        else:
            return res["f"]

    async def add_code_trigger(self, guild_id: int, code: str, roles: list) -> None:
        # UPDATE SERVER SET code_trigger = jsonb_set(code_trigger, '{%s}', $1::jsonb) where id = $2 # [code_trigger][code] = roles
        await self.con.execute("UPDATE SERVER SET code_trigger = jsonb_set(code_trigger, '{%s}', $1::jsonb) where id = $2" % code, json.dumps(roles), guild_id)

    async def remove_code_trigger(self, guild_id: int, code: str) -> None:
        """招待コードトリガーから設定されているコードを削除"""
        # UPDATE server set code_trigger = // code_triggerの値を更新
        # code_trigger - code // code_triggerの中のキーがcodeである要素を削除
        # WHERE id = guild_id // idがサーバーであるものに適用
        await self.con.execute("UPDATE server set code_trigger = code_trigger - $1 WHERE id = $2;", code, guild_id)

    async def get_user_trigger_list(self, guild_id: int) -> list:
        """ユーザートリガーに設定されているコードのリストを取得"""
        # SELECT array_agg(keys) FROM () r // keysを配列に整形して表示 (名前をつけないといけないため任意の名前r(AS r)を追加)
        # SELECT jsonb_object_keys(user_trigger) AS keys FROM server WHERE id = $1 // user_triggerのキー一覧を取得してkeysという名前で保存
        res = await self.con.fetchrow("""
            SELECT array_agg(keys) FROM (
                SELECT jsonb_object_keys(user_trigger) AS keys FROM server WHERE id = $1
            ) r
        """, guild_id)
        if res is None or res["array_agg"] is None:
            return []
        else:
            return res["array_agg"]

    async def get_user_trigger_count(self, guild_id: int) -> int:
        """ユーザートリガーの数を取得"""
        res = await self.con.fetchrow("select count(keys) from (select jsonb_object_keys(user_trigger) as keys from server where id = $1)r ;", guild_id)
        if res is None or res["count"]:
            return 0
        else:
            return res["count"]

    async def get_user_trigger_roles(self, guild_id: int, user_id: int) -> list:
        """ユーザートリガーに設定されている役職のリストを取得"""
        res = await self.con.fetchrow("SELECT user_trigger->>$1 AS f FROM server WHERE id = $2;", str(user_id), guild_id)
        if res is None or res["f"] is None:
            return []
        else:
            return res["f"]

    async def add_user_trigger(self, guild_id: int, user_id: int, roles: list) -> None:
        # UPDATE SERVER SET code_trigger = jsonb_set(code_trigger, '{%s}', $1::jsonb) where id = $2 # [user_trigger][user_id] = roles
        await self.con.execute("UPDATE SERVER SET user_trigger = jsonb_set(user_trigger, '{%d}', $1::jsonb) where id = $2" % user_id, json.dumps(roles), guild_id)

    async def remove_user_trigger(self, guild_id: int, user: int) -> None:
        """ユーザートリガーから設定されているコードを削除"""
        # UPDATE server set user_trigger = // user_triggerの値を更新
        # user_trigger - code // user_triggerの中のキーがcodeである要素を削除
        # WHERE id = guild_id // idがサーバーであるものに適用
        await self.con.execute("UPDATE server set user_trigger = user_trigger - $1 WHERE id = $2;", str(user), guild_id)

    async def add_invited_to_inviter(self, guild_id: int, inviter: int, invited: int) -> None:
        """招待履歴を招待者のデータに追加"""
        if await self.is_registered_user(guild_id, inviter):
            await self.register_new_user(guild_id, inviter)
        # UPDATE server SET users = jsonb_insert(users, '{%d, to, 0}', $1) // users[inviter][to]にある配列にinvitedを追加
        await self.con.execute("UPDATE server SET users = jsonb_insert(users, '{%d, to, 0}', $1)" % inviter, str(invited))

    async def add_inviter_to_invited(self, guild_id: int, inviter: int, invited: int) -> None:
        """招待元ユーザーデータを招待された人のデータに追加"""
        if await self.is_registered_user(guild_id, invited):
            await self.register_new_user(guild_id, invited)
        # UPDATE server SET users = jsonb_set(users, '{%d, from}, $1')) // users[invited][from]にinvitedを代入
        await self.con.execute("UPDATE server SET users = jsonb_set(users, '{%d, from}', $1)" % invited, str(inviter))

    async def register_new_user(self, guild_id: int, user_id: int) -> None:
        """新規ユーザーデータを追加"""
        init_data = {user_id: {"to": [], "from": None, "code": None}}
        await self.con.execute("UPDATE server SET users = users||$1::jsonb WHERE id = $2", json.dumps(init_data), guild_id)

    async def get_user_invite_from(self, guild_id: int, user_id: int) -> int:
        """特定ユーザーの招待元ユーザーIDを取得"""
        # SELECT users#>'{%d, from}' AS f FROM server WHERE id = $1 // [users][user_id][from]にある値を取得
        res = await self.con.fetchrow("SELECT users#>'{%d, from}' AS f FROM server WHERE id = $1;" % user_id, guild_id)
        if res is None or res["f"] is None:
            return None
        else:
            return res["f"]

    async def get_user_invite_code(self, guild_id: int, user_id: int) -> str:
        """特定ユーザーの参加時の招待コードを取得"""
        # SELECT users#>'{%d, code}' AS f FROM server WHERE id = $1 // [users][user_id][code]にある値を取得
        res = await self.con.fetchrow("SELECT users#>'{%d, code}' AS f FROM server WHERE id = $1;" % user_id, guild_id)
        if res is None or res["f"] is None:
            return None
        else:
            return res["f"]

    async def is_registered_user(self, guild_id: int, user_id: int) -> bool:
        """ユーザーがサーバーのユーザーリストに登録されているか確認"""
        # SELECT users ? $1 AS f FROM server WHERE id = $2 // idがguild_idであるもので、usersの中にinvitedというキーがあるかどうか
        res = await self.con.fetchrow("SELECT users ? $1 AS f FROM server WHERE id = $2;", str(user_id), guild_id)
        if res is None or not res["f"]:
            return False
        else:
            return True

    # TODO: サーバーキーエラーが出た場合新規追加