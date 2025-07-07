import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp
import urllib.parse, urllib.request, re

# Global initialization values
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix=".", intents=intents)

# Global variables
queues = {}
now_playing = {}
now_playing_lock = asyncio.Lock()
voice_clients = {}
youtube_base_url = 'https://www.youtube.com/'
youtube_results_url = youtube_base_url + 'results?'
youtube_watch_url = youtube_base_url + 'watch?v='
yt_dl_options = {"format": "bestaudio/best"}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)
discord.opus.load_opus
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}
paused = False
volume = 0.25

class MusicPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def start_playing(self, ctx, song_data):
        try:
            print(f"Starting to play: {song_data['title']}")
            ffmpeg_options_with_volume = {
                **ffmpeg_options,
                'options': f'-vn -filter:a "volume={volume}"'
            }
            player = discord.FFmpegOpusAudio(song_data['url'], **ffmpeg_options_with_volume)
            voice_client = voice_clients[ctx.guild.id]

            def after_playing(error):
                print(f"[start_playing] Attempting to start: {song_data['title']}")
                if error:
                    print(f"Playback error: {error}")
                else:
                    print("Song finished, triggering play_next")

                # Use bot.loop safely and only pass what’s needed
                coro = self.play_next_by_guild(ctx.guild.id)
                fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                try:
                    fut.result()  # Optional: wait for any errors
                except Exception as e:
                    print(f"[after_playing] Failed to queue next: {e}")

            voice_client.play(player, after=after_playing)
            async with now_playing_lock:
                now_playing[ctx.guild.id] = song_data
            await ctx.send(f"Now playing: {song_data['title']}")
        except Exception as e:
            await ctx.send(f"Error playing song: {e}")
            print(f"Error in start_playing: {e}")

    async def play_next_by_guild(self, guild_id):
        ctx_dummy = type('Ctx', (), {})()  # dummy ctx
        ctx_dummy.guild = discord.Object(id=guild_id)
        ctx_dummy.send = lambda *args, **kwargs: print(f"[Dummy send] {args}, {kwargs}")

        class DummyAuthor:
            voice = None
        ctx_dummy.author = DummyAuthor()

        # If you need the voice channel:
        try:
            vc = voice_clients[guild_id]
            if vc.is_connected():
                vc_channel = vc.channel
                ctx_dummy.author.voice = type('VoiceState', (), {'channel': vc_channel})()
        except Exception:
            pass

        await self.play_next(ctx_dummy)
    


    async def play_next(self, ctx):
        
        guild_id = ctx.guild.id
        print(f"[play_next] Called for guild {guild_id}")
        print(f"[play_next] Queue: {queues.get(guild_id)}")
        print(f"[play_next] Voice client: {voice_clients.get(guild_id)}")

        async with now_playing_lock:
            if guild_id in queues and queues[guild_id]:
                song_data = queues[guild_id].pop(0)
                now_playing[guild_id] = song_data
                print(f"[play_next] Next song: {song_data['title']}")

                voice_client = voice_clients.get(guild_id)
                if voice_client and voice_client.is_connected():
                    print("[play_next] Voice client is connected, playing next song")
                    await self.start_playing(ctx, song_data)
                else:
                    print("[play_next] Voice client missing or disconnected, trying to reconnect...")
                    try:
                        voice_client = await ctx.author.voice.channel.connect()
                        voice_clients[guild_id] = voice_client
                        await self.start_playing(ctx, song_data)
                    except Exception as e:
                        print(f"[play_next] Reconnect failed: {e}")
                        await ctx.send(f"Error reconnecting to voice: {e}")
            else:
                now_playing.pop(guild_id, None)
                print("[play_next] Queue is empty")
                await ctx.send("Queue is empty.")


    @commands.command(name="play")
    async def play(self, ctx, *, query):
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []

        try:
            if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_connected():
                print("Already connected")
                voice_client = voice_clients[ctx.guild.id]
            else:
                print("Attempting to connect to voice")
                voice_client = await ctx.author.voice.channel.connect()
                print("Connecting to voice")
                voice_clients[voice_client.guild.id] = voice_client
        except Exception as e:
            await ctx.send(f"Error connecting to voice channel: {e}")
            return

        if not query.startswith("http"):
            query = urllib.parse.urlencode({"search_query": query})
            html_content = urllib.request.urlopen(youtube_results_url + query)
            search_results = re.findall(r'/watch\?v=(.{11})', html_content.read().decode())
            if not search_results:
                await ctx.send("No results found!")
                return
            query = youtube_watch_url + search_results[0]

        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
            if 'entries' in data:
                data = data['entries'][0]
            title = data['title']
            url = data['url']
            song_data = {"title": title, "url": url}
            if voice_client.is_playing() or paused:
                queues[ctx.guild.id].append(song_data)

            if not voice_client.is_playing() and not paused:
                await self.start_playing(ctx, song_data)
        except Exception as e:
            await ctx.send(f"Error: {e}")

    def on_song_end(self, ctx, error):
        if error:
            print(f"Playback error: {error}")
        else:
            print("Song finished, triggering play_next")
            # Schedule the async function in the event loop
            asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

    @commands.command(name="clear")
    async def clear_queue(self, ctx):
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
            await ctx.send("Queue cleared!")
        else:
            await ctx.send("There is no queue to clear")

    @commands.command(name="pause")
    async def pause(self, ctx):
        try:
            voice_clients[ctx.guild.id].pause()
            global paused
            paused = True
        except Exception as e:
            await ctx.send(f"Error pausing: {e}")

    @commands.command(name="resume")
    async def resume(self, ctx):
        try:
            voice_clients[ctx.guild.id].resume()
            global paused
            paused = False
        except Exception as e:
            await ctx.send(f"Error resuming: {e}")

    @commands.command(name="stop")
    async def stop(self, ctx):
        try:
            voice_clients[ctx.guild.id].stop()
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]
            queues[ctx.guild.id].clear()
        except Exception as e:
            await ctx.send(f"Error stopping: {e}")

    @commands.command(name="queue")
    async def queue(self, ctx):
        try:
            async with now_playing_lock:
                guild_id = ctx.guild.id
                if guild_id in queues and queues[guild_id]:
                    queue_titles = [song['title'] for song in queues[guild_id]]
                    queue_str = "\n".join(queue_titles)

                    now_song = now_playing.get(guild_id)
                    now_title = now_song['title'] if now_song else "Nothing is playing"

                    await ctx.send(f"Currently playing: {now_title}\nCurrent queue:\n{queue_str}")
                else:
                    now_song = now_playing.get(guild_id)
                    now_title = now_song['title'] if now_song else "Nothing is playing"
                    await ctx.send(f"Currently playing: {now_title}\nThe queue is empty!")
        except Exception as e:
            await ctx.send(f"Error displaying queue: {e}")
            print(f"Queue command error: {e}")

    @commands.command(name='skip')
    async def skip(self, ctx):
        try:
            vc = voice_clients.get(ctx.guild.id)
            if vc and vc.is_playing():
                vc.stop()
                await ctx.send("Song skipped!")
            else:
                await ctx.send("Nothing is currently playing.")
        except Exception as e:
            await ctx.send(f"Error skipping song: {e}")



    #command for changing volume, currently non-functional, commented out to prevent issues.
    #    @commands.command(name="volume")
    #    async def volume(self, ctx, volume: float):
    #        if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_connected():
    #            voice_client = voice_clients[ctx.guild.id]
    #            if voice_client.is_playing():
    #                print(f"Current volume before adjustment: {voice_client.source.volume}")
    #                voice_client.source.volume = volume
    #                print(f"New volume after adjustment: {voice_client.source.volume}")
    #                await ctx.send(f"Volume set to {volume}")
    #            else:
    #                await ctx.send("No audio is currently playing.")
    #        else:
    #            await ctx.send("Not connected to a voice channel or no audio is playing.")

async def setup(bot):
    await bot.add_cog(MusicPlayer(bot))
