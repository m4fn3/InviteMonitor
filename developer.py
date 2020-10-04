from discord.ext import commands
from contextlib import redirect_stdout
import asyncio, datetime, discord, io, os, subprocess, sys, textwrap, time, traceback2, re
try:
    import psutil
except:
    psutil_available = False
else:
    psutil_available = True
from main import InvStat


# class
class Developer(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self.bot = bot  # type: InvStat
        self._last_result = None
        try:
            import psutil
        except:
            self.psutil = False
        else:
            self.psutil = True

    def cleanup_code(self, content):
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    async def cog_before_invoke(self, ctx):
        if ctx.author.id == self.bot.owner_id:
            raise Exception("Developer-Admin-Error")

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"引数が足りません。\nエラー詳細:\n{error}")
        else:
            await ctx.send(f"エラーが発生しました:\n{error}")

    @commands.group(aliases=["sys"])
    async def system(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("reload <Cog> | restart | quit")

    @system.command(aliases=["rl"])
    async def reload(self, ctx, text):
        if text in self.bot.bot_cogs:
            try:
                self.bot.reload_extension(text)
            except:
                await ctx.send(f"{text}の再読み込みに失敗しました\n{traceback2.format_exc()}.")
            else:
                await ctx.send(f"{text}の再読み込みに成功しました.")
        else:
            await ctx.send("存在しない名前です.")

    @system.command(aliases=["l"])
    async def load(self, ctx, text):
        if text in self.bot.bot_cogs:
            try:
                self.bot.load_extension(text)
            except:
                await ctx.send(f"{text}の読み込みに失敗しました\n{traceback2.format_exc()}.")
            else:
                await ctx.send(f"{text}の読み込みに成功しました.")
        else:
            await ctx.send("存在しない名前です.")

    @system.command(aliases=["u"])
    async def unload(self, ctx, text):
        if text in self.bot.bot_cogs:
            try:
                self.bot.unload_extension(text)
            except:
                await ctx.send(f"{text}の切り離しに失敗しました\n{traceback2.format_exc()}.")
            else:
                await ctx.send(f"{text}の切り離しに成功しました.")
        else:
            await ctx.send("存在しない名前です.")

    @system.command(aliases=["re"])
    async def restart(self, ctx):
        await ctx.send(":closed_lock_with_key:BOTを再起動します.")
        python = sys.executable
        os.execl(python, python, * sys.argv)

    @system.command(aliases=["q"])
    async def quit(self, ctx):
        await ctx.send(":closed_lock_with_key:BOTを停止します.")
        sys.exit()

    @commands.command()
    async def exe(self, ctx, *, body: str):
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
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
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

    @commands.command(aliases=["pr"])
    async def process(self, ctx):
        td = datetime.timedelta(seconds=int(time.time() - self.bot.uptime))
        m, s = divmod(td.seconds, 60)
        h, m = divmod(m, 60)
        d = td.days
        uptime = f"{d}d {h}h {m}m {s}s"
        if psutil_available:
            cpu_per = psutil.cpu_percent()
            mem_total = psutil.virtual_memory().total / 10**9
            mem_used = psutil.virtual_memory().used / 10**9
            mem_per = psutil.virtual_memory().percent
            swap_total = psutil.swap_memory().total / 10**9
            swap_used = psutil.swap_memory().used / 10**9
            swap_per = psutil.swap_memory().percent
        guilds = len(self.bot.guilds)
        users = len(self.bot.users)
        vcs = len(self.bot.voice_clients)
        text_channels = 0
        voice_channels = 0
        for channel in self.bot.get_all_channels():
            if isinstance(channel, discord.TextChannel):
                text_channels += 1
            elif isinstance(channel, discord.VoiceChannel):
                voice_channels += 1
        latency = self.bot.latency
        embed = discord.Embed(title="Process")
        if psutil_available:
            embed.add_field(name="Server", value=f"```yaml\nCPU: [{cpu_per}%]\nMemory: [{mem_per}%] {mem_used:.2f}GiB / {mem_total:.2f}GiB\nSwap: [{swap_per}%] {swap_used:.2f}GiB / {swap_total:.2f}GiB\n```", inline=False)
        embed.add_field(name="Discord", value=f"```yaml\nServers: {guilds}\nTextChannels: {text_channels}\nVoiceChannels: {voice_channels}\nUsers: {users}\nConnectedVC: {vcs}```", inline=False)
        embed.add_field(name="Run", value=f"```yaml\nUptime: {uptime}\nLatency: {latency:.2f}[s]\n```")
        await ctx.send(embed=embed)

    @commands.command()
    async def cmd(self, ctx, *, text):
        msg = ""
        try:
            output = await self.run_subprocess(text, loop=self.bot.loop)
            for i in range(len(output)):
                msg += output[i]
            await ctx.send(msg)
        except:
            await ctx.send(file=discord.File(fp=io.StringIO(msg), filename="output.txt"))

    async def run_subprocess(self, cmd, loop=None):
        loop = loop or asyncio.get_event_loop()
        try:
            process = await asyncio.create_subprocess_shell(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except NotImplementedError:
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True) as process:
                try:
                    result = await loop.run_in_executor(None, process.communicate)
                except Exception:  # muh pycodestyle
                    def kill():
                        process.kill()
                        process.wait()
                    await loop.run_in_executor(None, kill)
                    raise
        else:
            result = await process.communicate()

        return [res.decode('utf-8') for res in result]


def setup(bot):
    bot.add_cog(Developer(bot))