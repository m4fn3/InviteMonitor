from functools import wraps

import discord
import traceback2
from discord.ext import commands


async def error_embed_builder(sendable, text: str, title: str = None):
    embed = discord.Embed(description=f"<:xx:769783006302699548> {text}", color=discord.Color.red())
    if title:
        embed.title = title
    await sendable.send(embed=embed)


async def success_embed_builder(sendable, text: str, title: str = None):
    embed = discord.Embed(description=f"<:oo:769783006029414440> {text}", color=discord.Color.green())
    if title:
        embed.title = title
    await sendable.send(embed=embed)


async def warning_embed_builder(sendable, text: str, title: str = None):
    embed = discord.Embed(description=f"<:warn:769783006071881728> {text}", color=0xf7b51c)
    if title:
        embed.title = title
    await sendable.send(embed=embed)


async def normal_ember_builder(sendable, text: str, title: str = None):
    embed = discord.Embed(description=f"{text}", color=discord.Color.blue())
    if title:
        embed.title = title
    await sendable.send(embed=embed)


def is_author_has_manage():
    """サーバーの管理 権限を実行者が持っているか判定"""

    async def predicate(ctx):
        if not (ctx.author.guild_permissions.manage_guild and ctx.author.guild_permissions.manage_channels):
            await error_embed_builder(ctx, "You don't have __manage_guild, manage_channels__ permission!", title="Missing Permission")
            return False
        else:
            return True

    return commands.check(predicate)


def is_has_manage():
    """サーバーの管理 権限をBOTと実行者が持っているか判定"""

    async def predicate(ctx):
        if not (ctx.author.guild_permissions.manage_guild and ctx.author.guild_permissions.manage_channels):
            await error_embed_builder(ctx, "You don't have __manage_guild, manage_channels__ permission!", title="Missing Permission")
            return False
        elif not (ctx.guild.me.guild_permissions.manage_guild and ctx.guild.me.guild_permissions.manage_channels):
            await error_embed_builder(ctx, "I don't have __manage_guild, manage_channels__ permission!", title="Permission denied")
            return False
        else:
            return True

    return commands.check(predicate)


def is_has_kick_members():
    """メンバーをキック 権限をBOTと実行者が持っているか判定"""

    async def predicate(ctx):
        if not ctx.author.guild_permissions.kick_members:
            await error_embed_builder(ctx, "You don't have __kick_members__ permission!", title="Missing Permission")
            return False
        elif not ctx.guild.me.guild_permissions.kick_members:
            await error_embed_builder(ctx, "I don't have __kick_members__ permission!", title="Permission denied")
            return False
        else:
            return True

    return commands.check(predicate)


def is_has_ban_members():
    """メンバーをBAN 権限をBOTと実行者が持っているか判定"""

    async def predicate(ctx):
        if not ctx.author.guild_permissions.ban_members:
            await error_embed_builder(ctx, "You don't have __ban_members__ permission!", title="Missing Permission")
            return False
        elif not ctx.guild.me.guild_permissions.ban_members:
            await error_embed_builder(ctx, "I don't have __ban_members__ permission!", title="Permission denied")
            return False
        else:
            return True

    return commands.check(predicate)


def is_has_manage_roles():
    """役職の管理 権限をBOTと実行者が持っているか判定"""

    async def predicate(ctx):
        if not ctx.author.guild_permissions.manage_roles:
            await error_embed_builder(ctx, "You don't have __manage_roles__ permission!", title="Missing Permission")
            return False
        elif not ctx.guild.me.guild_permissions.manage_roles:
            await error_embed_builder(ctx, "I don't have __manage_roles__ permission!", title="Permission denied")
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


def debugger(func):
    @wraps(func)
    async def wrapped(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except Exception as e:
            orig_error = getattr(e, 'original', e)
            error_msg = ''.join(traceback2.TracebackException.from_exception(orig_error).format())
            await self.bot.get_channel(664376321278738453).send(f'```py\n{error_msg}```')

    return wrapped
