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

    async def get_trigger_code_list(self, guild_id: int) -> list:
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

    async def remove_trigger_code(self, guild_id: int, code: str) -> None:
        """招待コードトリガーから設定されているコードを削除"""
        # UPDATE server set code_trigger = // code_triggerの値を更新
        # code_trigger - code // code_triggerの中のキーがcodeである要素を削除
        # WHERE id = guild_id // idがサーバーであるものに適用
        await self.con.execute("UPDATE server set code_trigger = code_trigger - $1 WHERE id = $2;", code, guild_id)

    async def add_invite_to_inviter(self, guild_id: int, inviter: int, invited: int) -> None:
        # SELECT users ? $1 AS f FROM server WHERE id = $2 // idがguild_idであるもので、usersの中にinviterというキーがあるかどうか
        res = await self.con.fetchrow("SELECT users ? $1 AS f FROM server WHERE id = $2;", str(inviter), guild_id)
        if res is None or not res["f"]:  # キーが存在しない場合(=未登録の場合)
            await self.register_new_user(guild_id, inviter)
        # TODO: 既に同じIDが入っていないことを確認
        print(json.dumps([invited]))
        # TODO: users {"USERID": {"TO": []}} // TOに追加
        await self.con.execute("UPDATE server SET users = jsonb_set(users, '{to}', users->'to'||$1::jsonb)", json.dumps([invited]))

    async def register_new_user(self, guild_id: int, user_id: int) -> None:
        """新規ユーザーデータを追加"""
        init_data = {user_id: {"to_all": [], "to": [], "from": None, "code": None}}
        await self.con.execute("UPDATE server SET users = users||$1::jsonb WHERE id = $2", json.dumps(init_data), guild_id)

    # TODO: サーバーキーエラーが出た場合新規追加
