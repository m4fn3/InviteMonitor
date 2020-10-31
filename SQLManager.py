import json
from typing import Optional, List, Set

import asyncpg


class SQLManager:
    def __init__(self, database_url: str):
        self.con = None
        self.database_url = database_url

    # Connection
    async def connect(self) -> asyncpg.connection:
        """データベースに接続"""
        self.con = await asyncpg.connect(self.database_url)

    def is_connected(self) -> bool:
        """データベースに接続しているか確認"""
        if self.con is None:
            return False
        else:
            return True

    # Guild
    async def get_guild_ids(self) -> list:
        """登録されているサーバーIDのリストを取得"""
        # SELECT array_agg(id) FROM server // id列の値をすべて配列にして表示
        res = await self.con.fetchrow("SELECT array_agg(id) FROM server;")
        return dict(res)["array_agg"]

    async def is_enabled_guild(self, guild_id: int) -> bool:
        """特定のサーバーでモニターが有効になっているかどうかを確認"""
        res = await self.con.fetchrow("SELECT channel FROM server WHERE id = $1;", guild_id)
        if res is None or res["channel"] is None:
            return False
        else:
            return True

    async def enable_guild(self, guild_id: int, channel_id: int) -> None:
        """有効にする"""
        if not await self.is_registered_guild(guild_id):
            await self.register_new_guild(guild_id)
        await self.con.execute("UPDATE server SET channel = $1 WHERE id = $2;", channel_id, guild_id)

    async def disable_guild(self, guild_id: int) -> None:
        """無効にする"""
        await self.con.execute("UPDATE server SET channel = null WHERE id = $1;", guild_id)

    async def is_registered_guild(self, guild_id: int) -> bool:
        """サーバーが登録されているか確認"""
        res = await self.con.fetchrow("select count(*) from server where id = $1", guild_id)
        if res is None or res["count"] is None or res["count"] == 0:
            return False
        else:
            return True

    async def register_new_guild(self, guild_id: int) -> None:
        """新規サーバーのデータを追加"""
        await self.con.execute("INSERT INTO server values($1)", guild_id)

    async def get_guild_users_count(self, guild_id: int) -> int:
        """サーバーが認識しているユーザー数を取得"""
        res = await self.con.fetchrow("SELECT count(keys) FROM (SELECT jsonb_object_keys(users) AS keys FROM server WHERE id = $1)r ;", guild_id)
        if res is None or res["count"] is None:
            return 0
        else:
            return res["count"]

    async def get_guild_users(self, guild_id: int) -> list:
        """保存されているユーザーのリストを取得"""
        res = await self.con.fetchrow("SELECT array_agg(keys) FROM (SELECT jsonb_object_keys(users) AS keys FROM server WHERE id = $1)r ;", guild_id)
        if res is None or res["array_agg"] is None:
            return []
        else:
            return res["array_agg"]

    async def get_enabled_guild_ids(self) -> list:
        """登録されているサーバーIDのリストを取得"""
        # SELECT array_agg(id) FROM server WHERE channel is not null // channelがnullでない(=有効化されている)サーバーのidを配列で取得
        res = await self.con.fetchrow("SELECT array_agg(id) FROM server WHERE channel is not null;")
        if guild_ids := dict(res)["array_agg"]:  # データが存在する場合
            return guild_ids
        else:  # データが空の場合
            return []

    async def get_log_channel_id(self, guild_id: int) -> Optional[int]:
        """ログ送信用チャンネルを取得"""
        res = await self.con.fetchrow("SELECT channel FROM server WHERE id = $1", guild_id)
        if res is None or res["channel"] is None:
            return None
        else:
            return res["channel"]

    # Trigger
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
        if res is None or res["count"] is None:
            return 0
        else:
            return res["count"]

    async def get_code_trigger_roles(self, guild_id: int, code: str) -> list:
        """招待コードトリガーに設定されている役職のリストを取得"""
        res = await self.con.fetchrow("SELECT code_trigger->>$1 AS f FROM server WHERE id = $2;", code, guild_id)
        if res is None or res["f"] is None or res["f"] == "null":
            return []
        else:
            return json.loads(res["f"])  # 文字列で返って来るので手動で変換

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
        if res is None or res["count"] is None:
            return 0
        else:
            return res["count"]

    async def get_user_trigger_roles(self, guild_id: int, user_id: int) -> list:
        """ユーザートリガーに設定されている役職のリストを取得"""
        res = await self.con.fetchrow("SELECT user_trigger->>$1 AS f FROM server WHERE id = $2;", str(user_id), guild_id)
        if res is None or res["f"] is None or res["f"] == "null":
            return []
        else:
            return json.loads(res["f"])  # 文字列で返って来るので手動で変換

    async def add_user_trigger(self, guild_id: int, user_id: int, roles: list) -> None:
        # UPDATE SERVER SET code_trigger = jsonb_set(code_trigger, '{%s}', $1::jsonb) where id = $2 # [user_trigger][user_id] = roles
        await self.con.execute("UPDATE SERVER SET user_trigger = jsonb_set(user_trigger, '{%d}', $1::jsonb) where id = $2" % user_id, json.dumps(roles), guild_id)

    async def remove_user_trigger(self, guild_id: int, user: int) -> None:
        """ユーザートリガーから設定されているコードを削除"""
        # UPDATE server set user_trigger = // user_triggerの値を更新
        # user_trigger - code // user_triggerの中のキーがcodeである要素を削除
        # WHERE id = guild_id // idがサーバーであるものに適用
        await self.con.execute("UPDATE server set user_trigger = user_trigger - $1 WHERE id = $2;", str(user), guild_id)

    # Invites
    async def add_invited_to_inviter(self, guild_id: int, inviter: int, invited: int) -> None:
        """招待履歴を招待者のデータに追加"""
        if not await self.is_registered_user(guild_id, inviter):
            await self.register_new_user(guild_id, inviter)
        res = await self.con.fetchrow("select users->$1->'to' as f from server where id = $2;", str(inviter), guild_id)
        if res is not None and dict(res)["f"] is not None and invited in json.loads(dict(res)["f"]):
            return  # 既にユーザーが追加されている場合は終了
        # UPDATE server SET users = jsonb_insert(users, '{%d, to, 0}', $1) // users[inviter][to]にある配列にinvitedを追加
        await self.con.execute("UPDATE server SET users = jsonb_insert(users, '{%d, to, 0}', $1)" % inviter, str(invited))

    async def add_inviter_to_invited(self, guild_id: int, inviter: int, invited: int) -> None:
        """招待元ユーザーデータを招待された人のデータに追加"""
        if not await self.is_registered_user(guild_id, invited):
            await self.register_new_user(guild_id, invited)
        # UPDATE server SET users = jsonb_set(users, '{%d, from}, $1)) // users[invited][from]にinvitedを代入
        await self.con.execute("UPDATE server SET users = jsonb_set(users, '{%d, from}', $1)" % invited, str(inviter))

    async def add_code_to_invited(self, guild_id: int, code: str, invited: int) -> None:
        """使用した招待コードを招待された人のデータに追加"""
        if not await self.is_registered_user(guild_id, invited):
            await self.register_new_user(guild_id, invited)
        # UPDATE server SET users = jsonb_set(users, '{%d, from}, $1)) // users[invited][code]にinvitedを代入
        # 文字列を代入したい場合,'"string"'の形式にする必要があるため%で代入
        await self.con.execute("UPDATE server SET users = jsonb_set(users, '{%d, code}', '\"%s\"')" % (invited, code))

    # User
    async def register_new_user(self, guild_id: int, user_id: int) -> None:
        """新規ユーザーデータを追加"""
        init_data = {user_id: {"to": [], "from": None, "code": None, "uid": user_id}}
        await self.con.execute("UPDATE server SET users = users||$1::jsonb WHERE id = $2", json.dumps(init_data), guild_id)

    async def reset_user_data(self, guild_id: int, user_id: int):
        """既存ユーザーデータをクリア"""
        await self.con.execute("UPDATE SERVER SET users = jsonb_set(users, '{%d, to}', '[]'::jsonb) where id = $1" % user_id, guild_id)

    async def get_user_invite_count(self, guild_id: int, user_id: int) -> int:
        """特定ユーザーの招待数を取得"""
        res = await self.con.fetchrow("SELECT jsonb_array_length(users#>'{%d, to}') FROM server WHERE id = $1;" % user_id, guild_id)
        if res is None or res["jsonb_array_length"] is None:
            return 0
        else:
            return res["jsonb_array_length"]

    async def get_user_invite_from(self, guild_id: int, user_id: int) -> Optional[int]:
        """特定ユーザーの招待元ユーザーIDを取得"""
        # SELECT users#>'{%d, from}' AS f FROM server WHERE id = $1 // [users][user_id][from]にある値を取得
        res = await self.con.fetchrow("SELECT users#>'{%d, from}' AS f FROM server WHERE id = $1;" % user_id, guild_id)
        if res is None or res["f"] is None or res["f"] == "null":
            return None
        else:
            return int(res["f"])

    async def get_user_invite_code(self, guild_id: int, user_id: int) -> Optional[str]:
        """特定ユーザーの参加時の招待コードを取得"""
        # SELECT users#>'{%d, code}' AS f FROM server WHERE id = $1 // [users][user_id][code]にある値を取得
        res = await self.con.fetchrow("SELECT users#>'{%d, code}' AS f FROM server WHERE id = $1;" % user_id, guild_id)
        if res is None or res["f"] is None or res["f"] == "null":
            return None
        else:  # "CodeTEsT" -> CodeTEsT
            return res["f"].strip('"')  # 普通のテキストとして取得するので,でコードされないので,手動でデコードする

    async def is_registered_user(self, guild_id: int, user_id: int) -> bool:
        """ユーザーがサーバーのユーザーリストに登録されているか確認"""
        # SELECT users ? $1 AS f FROM server WHERE id = $2 // idがguild_idであるもので、usersの中にinvitedというキーがあるかどうか
        res = await self.con.fetchrow("SELECT users ? $1 AS f FROM server WHERE id = $2;", str(user_id), guild_id)
        if res is None or not res["f"]:
            return False
        else:
            return True

    async def filter_with_code_and_from(self, code_list: List[str], from_list: List[str], guild_id: int) -> Set[int]:
        """指定した招待コードまたは招待者によって参加した人のIDリストを取得"""
        sql = ""
        # @.code like_regex "code1|code2" ... 招待コードがcode1またはcode2であるならば
        if code_list:
            sql += "@.code like_regex \"" + "|".join([f"{i}" for i in code_list]) + "\""
        if from_list:
            # @from == 128319 || @from == 198733 ... 招待者が128319か198733ならば
            from_sql = "@.from == " + f" || @.from == ".join(from_list)
            if sql:  # 招待コードの条件があった場合は OR の記号を追加
                sql += "||" + from_sql
            else:
                sql += from_sql
        id_list = set()
        # SELECT jsonb_path_query(users, '$.* ? (%s)') FROM server; ... 任意のキー内の条件に合う値を取得
        res = await self.con.fetch("SELECT jsonb_path_query(users, '$.* ? (%s)') FROM server where id = $1;" % sql, guild_id)
        for record in res:
            id_list.add(json.loads(record['jsonb_path_query'])["uid"])
        return id_list

    # TODO: asyncpg同時に asyncpg.exceptions._base.InterfaceError: cannot perform operation: another operation is in progress になる問題