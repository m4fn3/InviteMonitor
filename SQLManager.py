import asyncpg


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
        res = await self.con.fetchrow("select array_agg(id) from server;")
        return dict(res)["array_agg"]

    async def is_enabled_guild(self, guild_id: int) -> bool:
        """特定のサーバーでモニターが有効になっているかどうかを確認"""
        res = await self.con.fetchrow("select count(*) from server where channel is not null and id = $1;", guild_id)
        return bool(res)

    async def register_new_guild(self, guild_id: int) -> None:
        """新規サーバーのデータを追加"""
        await self.con.execute("insert into server values($1)", guild_id)

    async def get_enabled_guild_ids(self) -> list:
        """登録されているサーバーIDのリストを取得"""
        res = await self.con.fetchrow("select array_agg(id) from server where channel is not null;")
        return dict(res)["array_agg"]

    # TODO: サーバーキーエラーが出た場合新規追加




