import discord
import nacl
import os
import json
import yt_dlp
from dotenv import load_dotenv
from discord.ext import commands, tasks

load_dotenv()

TOKEN = os.getenv("TOKEN")

VOICE_FILE = "voice_channel.json"

intents = discord.Intents.default()
intents.message_content = True
music_queue = []
loop_enabled = False
autoplay_enabled = True
current_song = None
last_query = None
volume_level = 0.5

bot = commands.Bot(
    command_prefix="$",
    intents=intents
)

YTDL_OPTIONS = {
    "format": "bestaudio",
    "noplaylist": False,
    "quiet": True
}

FFMPEG_OPTIONS = {

    "before_options":

    "-reconnect 1 "
    "-reconnect_streamed 1 "
    "-reconnect_delay_max 5 "
    "-nostdin",

    "options":

    "-vn "
    "-bufsize 512k"

}
@bot.event
async def on_ready():

    print(
        f"✅ Music Bot Online: "
        f"{bot.user}"
    )

    if not vc_watchdog.is_running():

        vc_watchdog.start()

    # Rejoin saved VC
    try:

        with open(
            VOICE_FILE,
            "r"
        ) as f:

            data = json.load(f)

        channel_id = data.get(
            "channel_id"
        )

        if channel_id:

            channel = bot.get_channel(
                channel_id
            )

            if channel:

                await channel.connect()

                print(
                    "🎵 Rejoined Music VC"
                )

    except FileNotFoundError:

        print(
            "No saved VC yet"
        )

    except Exception as e:

        print(
            "VC restore error:",
            e
        )

@tasks.loop(seconds=30)
async def vc_watchdog():

    for guild in bot.guilds:

        try:

            if guild.voice_client is None:

                with open(
                    VOICE_FILE,
                    "r"
                ) as f:

                    data = json.load(f)

                channel_id = data.get(
                    "channel_id"
                )

                if channel_id:

                    channel = bot.get_channel(
                        channel_id
                    )

                    if channel:

                        await channel.connect()

                        print(
                            "🎵 Auto rejoined VC"
                        )

        except Exception as e:

            print(
                "VC watchdog error:",
                e
            )

async def play_music(ctx, query):

    global current_song
    global current_title
    global last_query

    vc = ctx.voice_client

    if not vc:

        await ctx.send(
            "Bot not in VC"
        )
        return

    try:

        await ctx.send(
            "🔍 Searching..."
        )

        last_query = query

        ydl_options = {

            "format":
            "bestaudio/best",

            "quiet":
            True,

            "extract_flat":
            False,

            "source_address":
            "0.0.0.0",

            "default_search":
            "ytsearch",

            "noplaylist":
            False
        }

        with yt_dlp.YoutubeDL(
            ydl_options
        ) as ydl:

            info = ydl.extract_info(

                query,

                download=False

            )

            # Playlist
            # Playlist or search result
            if "entries" in info:
            
                entries = list(
                    info["entries"]
                )
            
                # Song name search
                if not query.startswith(
                    "http"
                ):
            
                    first_entry = entries[0]
            
                    url = first_entry["url"]
            
                    title = first_entry.get(
                        "title",
                        "Unknown"
                    )
            
                    if vc.is_playing() or vc.is_paused():
            
                        music_queue.append({
            
                            "url":
                            url,
            
                            "title":
                            title
                        })
            
                        await ctx.send(
            
                            f"➕ Added to queue:\n"
                            f"{title}"
            
                        )
            
                        return
            
                    current_song = url
                    current_title = title
            
                    source = discord.PCMVolumeTransformer(
                    
                        discord.FFmpegPCMAudio(
                    
                            current_song,
                    
                            **FFMPEG_OPTIONS
                    
                        ),
                    
                        volume=volume_level
                    )
            
                    vc.play(
                        source,
                    
                        after=lambda e:
                        asyncio.run_coroutine_threadsafe(
                            play_next(ctx),
                            bot.loop
                        )
                    )
            
                    await ctx.send(
            
                        f"🎵 Now Playing:\n"
                        f"{title}"
            
                    )
            
                    return
            
                # Playlist link
                for entry in entries:
            
                    if entry:
            
                        music_queue.append({
            
                            "url":
                            entry["url"],
            
                            "title":
                            entry.get(
                                "title",
                                "Unknown"
                            )
                        })
            
                await ctx.send(
            
                    f"📜 Added "
                    f"{len(entries)} "
                    f"songs to queue"
            
                )
            
                return

            else:

                url = info["url"]

                title = info.get(
                    "title",
                    "Unknown"
                )

                # Already playing → queue
                # Queue only if actually playing or paused
                if vc.is_playing() or vc.is_paused():
                
                    music_queue.append({
                
                        "url":
                        url,
                
                        "title":
                        title
                    })
                
                    await ctx.send(
                
                        f"➕ Added to queue:\n"
                        f"{title}"
                
                    )
                
                    return
                current_song = url
                current_title = title

                source = discord.FFmpegPCMAudio(

                    current_song,

                    **FFMPEG_OPTIONS
                )

                vc.play(
                
                    source,
                
                    after=lambda e:
                    asyncio.run_coroutine_threadsafe(
                        play_next(ctx),
                        bot.loop
                    )
                )
                
                await asyncio.sleep(1)
                
                await ctx.send(
                
                    f"🎵 Now Playing:\n"
                    f"{title}"
                )

    except Exception as e:

        print(e)

        await ctx.send(
            "❌ Could not play music"
        )
async def play_next(ctx):

    global current_song
    global current_title

    vc = ctx.voice_client

    if not vc:
        return

    # Loop same song
    if loop_enabled and current_song:

        source = discord.PCMVolumeTransformer(
        
            discord.FFmpegPCMAudio(
        
                current_song,
        
                **FFMPEG_OPTIONS
        
            ),
        
            volume=volume_level
        )

        vc.play(
            source,
                    
            after=lambda e:
            asyncio.run_coroutine_threadsafe(
                play_next(ctx),
                bot.loop
            )
        )
        return

    # Queue system
    if len(music_queue) > 0:

        next_song = music_queue.pop(0)

        current_song = next_song["url"]
        current_title = next_song["title"]

        source = discord.FFmpegPCMAudio(

            current_song,

            **FFMPEG_OPTIONS
        )

        vc.play(

            source,

            after=lambda e:
            bot.loop.create_task(
                play_next(ctx)
            )
        )

        channel = vc.guild.text_channels[0]

        await channel.send(

            f"🎵 Now Playing:\n"
            f"{current_title}"
        )
        # Autoplay system
        if (
        
            autoplay_enabled
        
            and
        
            last_query
        
        ):
        
            try:
        
                await ctx.send(
                    "🎶 Autoplay finding next song..."
                )
        
                await play_music(
        
                    ctx,
        
                    f"{last_query} similar songs"
        
                )
        
            except Exception as e:
        
                print(
                    "Autoplay error:",
                    e
                )

@bot.command()
async def join(ctx):

    channel = discord.utils.get(

        ctx.guild.voice_channels,

        name="music"

    )

    if not channel:

        await ctx.send(
            "❌ music VC not found"
        )

        return

    vc = ctx.voice_client

    if vc is None:

        await channel.connect()

    elif vc.channel != channel:

        await vc.move_to(
            channel
        )

    with open(
        VOICE_FILE,
        "w"
    ) as f:

        json.dump(
            {
                "channel_id":
                channel.id
            },
            f
        )

    await ctx.send(
        "🎵 Music bot joined Music VC"
    )

@bot.command()
async def leave(ctx):

    if ctx.voice_client:

        await ctx.voice_client.disconnect()

        await ctx.send(
            "👋 Left VC"
        )


@bot.command()
async def ping(ctx):

    await ctx.send(
        "🏓 Music bot working!"
    )
@bot.command()
async def play(
    ctx,
    *,
    query
):

    if not ctx.voice_client:

        if ctx.author.voice:

            await ctx.author.voice.channel.connect()

        else:

            await ctx.send(
                "Join VC first"
            )

            return

    await play_music(
        ctx,
        query
    )
@bot.command()
async def stop(ctx):

    vc = ctx.voice_client

    if vc and vc.is_playing():

        vc.stop()

        await ctx.send(
            "⏹️ Music stopped"
        )

    else:

        await ctx.send(
            "Nothing playing"
        )


@bot.command()
async def pause(ctx):

    vc = ctx.voice_client

    if vc and vc.is_playing():

        vc.pause()

        await ctx.send(
            "⏸️ Music paused"
        )

    else:

        await ctx.send(
            "Nothing playing"
        )


@bot.command()
async def resume(ctx):

    vc = ctx.voice_client

    if vc and vc.is_paused():

        vc.resume()

        await ctx.send(
            "▶️ Music resumed"
        )

    else:

        await ctx.send(
            "Nothing paused"
        )
@bot.command()
async def skip(ctx):

    vc = ctx.voice_client

    if vc and vc.is_playing():

        vc.stop()

        await ctx.send(
            "⏭️ Skipped"
        )

    else:

        await ctx.send(
            "Nothing playing"
        )
@bot.command()
async def queue(ctx):

    if len(music_queue) == 0:

        await ctx.send(
            "📭 Queue empty"
        )

        return

    queue_text = ""

    for i, song in enumerate(
        music_queue[:10],
        start=1
    ):

        queue_text += (

            f"{i}. "
            f"{song['title']}\n"

        )

    await ctx.send(

        f"🎶 Queue:\n\n"
        f"{queue_text}"

    )
@bot.command()
async def loop(ctx, mode=None):

    global loop_enabled

    if mode is None:

        status = (
            "ON 😄"
            if loop_enabled
            else "OFF"
        )

        await ctx.send(
            f"🔁 Loop is {status}"
        )

        return

    mode = mode.lower()

    if mode == "on":

        loop_enabled = True

        await ctx.send(
            "🔁 Loop enabled"
        )

    elif mode == "off":

        loop_enabled = False

        await ctx.send(
            "⏹️ Loop disabled"
        )

    else:

        await ctx.send(
            "Use: $loop on/off"
        )
@bot.command()
async def nowplaying(ctx):

    if current_title:

        await ctx.send(

            f"🎵 Now Playing:\n"
            f"{current_title}"

        )

    else:

        await ctx.send(
            "Nothing playing"
        )
@bot.command()
async def clearqueue(ctx):

    music_queue.clear()

    await ctx.send(
        "🗑️ Queue cleared"
    )
@bot.command()
async def volume(ctx, level: int):

    global volume_level

    if level < 0 or level > 200:

        await ctx.send(
            "Use volume 0-200"
        )

        return

    volume_level = level / 100
    vc = ctx.voice_client

    if (

        vc
        and

        vc.source

        and

        hasattr(
            vc.source,
            "volume"
        )

    ):

        vc.source.volume = (
            volume_level
        )

        print(volume_level)

        await ctx.send(

            f"🔊 Volume set to "
            f"{level}%"

        )
@bot.command()
async def autoplay(ctx, mode=None):

    global autoplay_enabled

    if mode is None:

        status = (

            "ON 😄"
            if autoplay_enabled
            else "OFF"

        )

        await ctx.send(

            f"🔁 Autoplay is "
            f"{status}"

        )

        return

    mode = mode.lower()

    if mode == "on":

        autoplay_enabled = True

        await ctx.send(
            "▶️ Autoplay enabled"
        )

    elif mode == "off":

        autoplay_enabled = False

        await ctx.send(
            "⏹️ Autoplay disabled"
        )

    else:

        await ctx.send(
            "Use: $autoplay on/off"
        )

bot.run(TOKEN)