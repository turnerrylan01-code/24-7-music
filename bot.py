import os
import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import yt_dlp as youtube_dl

# Load environment variables
load_dotenv()

# Initialize Discord bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(command_prefix='!', intents=intents, activity=discord.Game(name="Music 24/7"))

    async def setup_hook(self):
        await self.tree.sync()
        print("Commands synced!")

bot = MyBot()

# Store the target voice channel ID
target_voice_channel_id = None  # Will be set via command

# Spotify setup
# Initialize Spotify with environment variables
client_id = os.getenv('SPOTIPY_CLIENT_ID') or os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET') or os.getenv('SPOTIFY_CLIENT_SECRET')

if not client_id or not client_secret:
    print("Warning: Spotify API credentials not found. Some features may not work.")
    sp = None
else:
    # Initialize Spotify with client credentials flow (no redirect URI needed)
    auth_manager = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)

# YTDL options
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

yt_dl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: yt_dl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else yt_dl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class MusicBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.playlist = []
        self.current_song = 0
        self.voice_channel = None
        self.spotify_playlist_id = os.getenv('SPOTIFY_PLAYLIST_ID')
        self.player_loop.start()
        self.volume = 0.5  # Default volume (50%)

    def cog_unload(self):
        self.player_loop.cancel()
    
    async def join_voice_channel(self, interaction: discord.Interaction):
        """Joins the configured voice channel"""
        global target_voice_channel_id
        if not target_voice_channel_id:
            await interaction.response.send_message("❌ No voice channel ID has been set. Use `/setchannel` first.", ephemeral=True)
            return False

        try:
            channel = self.bot.get_channel(target_voice_channel_id)
            if not channel or not isinstance(channel, discord.VoiceChannel):
                await interaction.response.send_message("❌ Invalid voice channel ID. Please set a valid voice channel ID first.", ephemeral=True)
                return False

            if interaction.guild.voice_client is not None:
                await interaction.guild.voice_client.move_to(channel)
            else:
                self.voice_channel = await channel.connect()
            
            return True
        except Exception as e:
            print(f"Error joining voice channel: {e}")
            await interaction.response.send_message(f"❌ Failed to join voice channel: {e}", ephemeral=True)
            return False

    @tasks.loop(seconds=10.0)
    async def player_loop(self):
        if not self.voice_channel or not self.voice_channel.is_connected():
            return

        if not self.playlist:
            await self.load_spotify_playlist()
            if not self.playlist:
                return

        voice_client = self.voice_channel.guild.voice_client
        
        if not voice_client.is_playing() and not voice_client.is_paused():
            if self.current_song >= len(self.playlist):
                self.current_song = 0
                
            song_url = self.playlist[self.current_song]
            try:
                player = await YTDLSource.from_url(song_url, loop=self.bot.loop)
                voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
                print(f'Now playing: {player.title}')
                self.current_song += 1
            except Exception as e:
                print(f'Error playing song: {e}')
                self.current_song += 1

    async def load_spotify_playlist(self):
        if not sp:
            print("Spotify client not initialized. Please check your credentials.")
            return False
            
        try:
            results = sp.playlist_tracks(self.spotify_playlist_id)
            tracks = results['items']
            
            while results['next']:
                results = sp.next(results)
                tracks.extend(results['items'])
            
            self.playlist = []
            for item in tracks:
                track = item['track']
                if track:
                    query = f"{track['name']} {track['artists'][0]['name']}"
                    # Search YouTube for the song
                    with youtube_dl.YoutubeDL(ytdl_format_options) as ydl:
                        info = ydl.extract_info(f"ytsearch:{query}", download=False)
                        if 'entries' in info and info['entries']:
                            self.playlist.append(info['entries'][0]['webpage_url'])
            
            print(f'Loaded {len(self.playlist)} songs from Spotify playlist')
            return True
            
        except Exception as e:
            print(f'Error loading Spotify playlist: {e}')
            return False

    @app_commands.command(name="setchannel", description="Set the voice channel for the bot to join")
    @app_commands.describe(channel_id="The ID of the voice channel")
    async def set_channel(self, interaction: discord.Interaction, channel_id: str):
        """Set the target voice channel by ID"""
        global target_voice_channel_id
        try:
            channel_id = int(channel_id)
            channel = self.bot.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.VoiceChannel):
                await interaction.response.send_message("❌ Invalid voice channel ID. Please provide a valid voice channel ID.", ephemeral=True)
                return
                
            target_voice_channel_id = channel_id
            await interaction.response.send_message(f"✅ Set voice channel to: {channel.name} (ID: {channel_id})")
        except ValueError:
            await interaction.response.send_message("❌ Please provide a valid channel ID (numbers only).", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

    @app_commands.command(name="join", description="Make the bot join the configured voice channel")
    async def join_command(self, interaction: discord.Interaction):
        """Join the configured voice channel and start playing"""
        await interaction.response.defer()
        if await self.join_voice_channel(interaction):
            if not self.playlist:
                await self.load_spotify_playlist()
            await interaction.followup.send("🎵 Joined voice channel and started playing!")

    @app_commands.command(name="leave", description="Make the bot leave the voice channel")
    async def leave_command(self, interaction: discord.Interaction):
        """Leave the current voice channel"""
        if interaction.guild.voice_client is not None:
            await interaction.guild.voice_client.disconnect()
            self.playlist = []
            self.current_song = 0
            await interaction.response.send_message("👋 Left the voice channel")
        else:
            await interaction.response.send_message("❌ I'm not in a voice channel!", ephemeral=True)

    @app_commands.command(name="volume", description="Set the bot's volume (0-100)")
    @app_commands.describe(volume="Volume level (0-100)")
    async def volume_command(self, interaction: discord.Interaction, volume: int):
        """Adjust the playback volume"""
        if not 0 <= volume <= 100:
            await interaction.response.send_message("❌ Volume must be between 0 and 100", ephemeral=True)
            return
            
        if interaction.guild.voice_client is None:
            await interaction.response.send_message("❌ I'm not in a voice channel!", ephemeral=True)
            return
            
        self.volume = volume / 100
        if interaction.guild.voice_client.source:
            interaction.guild.voice_client.source.volume = self.volume
            
        await interaction.response.send_message(f"🔊 Volume set to {volume}%")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')
    await bot.add_cog(MusicBot(bot))

# Get Discord token
discord_token = os.getenv('DISCORD_TOKEN')
if not discord_token:
    print("ERROR: No Discord token found. Please set the DISCORD_TOKEN environment variable.")
    print("You can get your token from: https://discord.com/developers/applications")
    exit(1)

# Run the bot
print("Starting bot...")
try:
    bot.run(discord_token)
except Exception as e:
    print(f"Failed to start bot: {e}")
    print("Please check your DISCORD_TOKEN and try again.")
