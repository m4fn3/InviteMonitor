from discord.ext import commands
from contextlib import redirect_stdout
import discord, traceback2, io, textwrap

class Invite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # type: commands.Bot

    @commands.command(aliases=["su", "set_up", "set-up"])
    async def setup(self, ctx):
        # 設定前に権限を確認
        if not self.bot.check_permission(ctx.guild):
            return await ctx.send("`manage_guild`権限が不足しています!チャンネルを設定する前に権限を付与してください.")
        # 対象チャンネルを取得
        target_channel: discord.TextChannel
        if not len(ctx.message.channel_mentions):
            target_channel = ctx.channel
        else:
            target_channel = ctx.message.channel_mentions[0]
        # チャンネルデータを保存
        self.bot.db[str(ctx.guild.id)]["channel"] = target_channel.id
        await ctx.send(f"{target_channel.mention}をログ用チャンネルに設定しました.")

    @commands.command(aliases=["st"])
    async def status(self, ctx):
        # そのサーバーでログが設定されているか確認
        if self.bot.db[str(ctx.guild.id)]["channel"] is None:
            return await ctx.send("このサーバーではログが設定されていません!設定するには`i/setup #チャンネル`を実行してください.")
        # 設定を取得
        embed = discord.Embed(title="Log Settings Status")
        embed.add_field(name="チャンネル", value=f"<#{self.bot.db[str(ctx.guild.id)]['channel']}>")
        embed.add_field(name="招待元把握済メンバー数", value=f"{len(self.bot.db[str(ctx.guild.id)]['users'])}")
        await ctx.send(embed=embed)

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    @commands.command()
    async def exe(self, ctx, *, body: str):
        # TODO: ADMIN実装後に修正
        if ctx.author.id != 513136168112750593: return
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback2.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                await ctx.send(f'```py\n{value}{ret}\n```')


def setup(bot):
    bot.add_cog(Invite(bot))
