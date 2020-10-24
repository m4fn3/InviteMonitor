from discord.ext import commands


def is_author_has_manage_guild():
    """サーバーの管理 権限を実行者が持っているか判定"""
    async def predicate(ctx):
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.send(":no_pedestrians: You don't have **__manage_guild__** permission!\nFor security reasons, this command can only be used by person who has permission.")
            return False
        else:
            return True
    return commands.check(predicate)

def is_has_manage_guild():
    """サーバーの管理 権限をBOTと実行者が持っているか判定"""
    async def predicate(ctx):
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.send(":no_pedestrians: You don't have **__manage_guild__** permission!\nFor security reasons, this command can only be used by person who has permission.")
            return False
        elif not ctx.guild.me.guild_permissions.manage_guild:
            await ctx.send(":no_entry_sign: BOT doesn't have **__manage_guild__** permission!")
            return False
        else:
            return True
    return commands.check(predicate)

def is_has_kick_members():
    """メンバーをキック 権限をBOTと実行者が持っているか判定"""
    async def predicate(ctx):
        if not ctx.author.guild_permissions.kick_members:
            await ctx.send(":no_pedestrians: You don't have **__kick_guild__** permission!\nFor security reasons, this command can only be used by person who has permission.")
            return False
        elif not ctx.guild.me.guild_permissions.kick_members:
            await ctx.send(":no_entry_sign: BOT doesn't have **__kick_guild__** permission!")
            return False
        else:
            return True
    return commands.check(predicate)

def is_has_ban_members():
    """メンバーをBAN 権限をBOTと実行者が持っているか判定"""
    async def predicate(ctx):
        if not ctx.author.guild_permissions.ban_members:
            await ctx.send(":no_pedestrians: You don't have **__ban_members__** permission!\nFor security reasons, this command can only be used by person who has permission.")
            return False
        elif not ctx.guild.me.guild_permissions.ban_members:
            await ctx.send(":no_entry_sign: BOT doesn't have **__ban_members__** permission!")
            return False
        else:
            return True
    return commands.check(predicate)

def is_has_manage_roles():
    """役職の管理 権限をBOTと実行者が持っているか判定"""
    async def predicate(ctx):
        if not ctx.author.guild_permissions.manage_roles:
            await ctx.send(":no_pedestrians: You don't have **__manage_roles__** permission!\nFor security reasons, this command can only be used by person who has permission.")
            return False
        elif not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(":no_entry_sign: BOT doesn't have **__manage_roles__** permission!")
            return False
        else:
            return True
    return commands.check(predicate)

def filter_hidden_commands(command_list, sort=False):
    """コマンドリストの中から隠し属性を持つコマンドを削除"""
    res = [cmd for cmd in command_list if not cmd.hidden]
    if sort:
        res.sort(key=lambda cmd: cmd.qualified_name)
    return res
