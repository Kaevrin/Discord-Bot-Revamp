import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp
import urllib.parse, urllib.request, re

intents = discord.Intents.default()

intents.message_content = True
client = commands.Bot(command_prefix='.', intents=intents)

queues = {}
now_playing  = {}
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

            voice_client.play(player)
            async with now_playing_lock:
                now_playing[ctx.guild.id] = song_data
            await ctx.send(f"Now playing: {song_data['title']}")
        except Exception as e:
            await ctx.send(f"Error playing song: {e}")
            print(f"Error in start_playing: {e}")


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

        #Connect to voice
        try:
            channel = ctx.author.voice.channel
            perms = channel.permissions_for(ctx.guild.me)
            print(f"[DEBUG] Bot permissions: CONNECT={perms.connect}, SPEAK={perms.speak}")

            if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_connected():
                print("Already connected")
                voice_client = voice_clients[ctx.guild.id]
            else:
                print("Attempting to connect to voice")
                try:
                    voice_client = await ctx.author.voice.channel.connect()
                    print("Connected to voice")
                    voice_clients[ctx.guild.id] = voice_client
                except Exception as e:
                    await ctx.send(f"Error connecting to voice channel: {e}")
                    return  # Make sure we stop if connection fails
                print("Connecting to voice")
                voice_clients[voice_client.guild.id] = voice_client
        except Exception as e:
            await ctx.send(f"Error connecting to voice channel: {e}")
            return

        #Process audio
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
        except Exception as e:
            await ctx.send(f"Error retrieving audio info: {e}")
            return

        # Start playing in voice
        try:
            if voice_client.is_playing() or paused:
                queues[ctx.guild.id].append(song_data)
                await ctx.send(f"Added to queue: {title}")
            else:
                await self.start_playing(ctx, song_data)
        except Exception as e:
            await ctx.send(f"Error playing song: {e}")

    @commands.command(name="pause")
    async def pause(self, ctx):
        if not paused:
            try:
                voice_clients[ctx.guild.id].pause()
                paused = True
            except Exception as e:
                await ctx.send(f"Error pausing: {e}")
        else:
            try:
                voice_clients[ctx.guild.id].resume()
                paused = False
            except Exception as e:
                await ctx.send(f"Error resuming: {e}")

    @commands.command(name="resume")
    async def resume(self, ctx):
        try:
            voice_clients[ctx.guild.id].resume()
            paused = False
        except Exception as e:
            await ctx.send(f"Error resuming: {e}")




async def setup(bot):
    await bot.add_cog(MusicPlayer(bot))