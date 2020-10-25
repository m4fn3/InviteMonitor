from discord.ext import commands
import discord


def is_author_has_manage_guild():
    """サーバーの管理 権限を実行者が持っているか判定"""
    async def predicate(ctx):
        if not ctx.author.guild_permissions.manage_guild:
            embed = discord.Embed(title="Missing Permission", description="You don't have __manage_guild__ permission!", color=discord.Color.red())
            await ctx.send(embed=embed)
            return False
        else:
            return True
    return commands.check(predicate)

def is_has_manage_guild():
    """サーバーの管理 権限をBOTと実行者が持っているか判定"""
    async def predicate(ctx):
        if not ctx.author.guild_permissions.manage_guild:
            embed = discord.Embed(title="Missing Permission", description="You don't have __manage_guild__ permission!", color=discord.Color.red())
            await ctx.send(embed=embed)
            return False
        elif not ctx.guild.me.guild_permissions.manage_guild:
            embed = discord.Embed(title="Permission denied", description="I don't have __manage_guild__ permission!", color=discord.Color.red())
            await ctx.send(embed=embed)
            return False
        else:
            return True
    return commands.check(predicate)

def is_has_kick_members():
    """メンバーをキック 権限をBOTと実行者が持っているか判定"""
    async def predicate(ctx):
        if not ctx.author.guild_permissions.kick_members:
            embed = discord.Embed(title="Missing Permission", description="You don't have __kick_members__ permission!", color=discord.Color.red())
            await ctx.send(embed=embed)
            return False
        elif not ctx.guild.me.guild_permissions.kick_members:
            embed = discord.Embed(title="Permission denied", description="I don't have __kick_members__ permission!", color=discord.Color.red())
            await ctx.send(embed=embed)
            return False
        else:
            return True
    return commands.check(predicate)

def is_has_ban_members():
    """メンバーをBAN 権限をBOTと実行者が持っているか判定"""
    async def predicate(ctx):
        if not ctx.author.guild_permissions.ban_members:
            embed = discord.Embed(title="Missing Permission", description="You don't have __ban_members__ permission!", color=discord.Color.red())
            await ctx.send(embed=embed)
            return False
        elif not ctx.guild.me.guild_permissions.ban_members:
            embed = discord.Embed(title="Permission denied", description="I don't have __ban_members__ permission!", color=discord.Color.red())
            await ctx.send(embed=embed)
            return False
        else:
            return True
    return commands.check(predicate)

def is_has_manage_roles():
    """役職の管理 権限をBOTと実行者が持っているか判定"""
    async def predicate(ctx):
        if not ctx.author.guild_permissions.manage_roles:
            embed = discord.Embed(title="Missing Permission", description="You don't have __manage_roles__ permission!", color=discord.Color.red())
            await ctx.send(embed=embed)
            return False
        elif not ctx.guild.me.guild_permissions.manage_roles:
            embed = discord.Embed(title="Permission denied", description="I don't have __manage_roles__ permission!", color=discord.Color.red())
            await ctx.send(embed=embed)
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
