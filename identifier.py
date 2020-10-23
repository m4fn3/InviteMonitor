from discord.ext import commands

def is_author_has_manage_guild():
    async def predicate(ctx):
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.send(":no_pedestrians: You don't have **__manage_guild__** permission!\nFor security reasons, this command can only be used by person who has permission.")
            return False
        else:
            return True
    return commands.check(predicate)

def is_has_manage_guild():
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
