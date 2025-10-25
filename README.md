# 24/7 Spotify Discord Music Bot

A Discord bot that plays your Spotify playlist 24/7 in a voice channel.

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- FFmpeg installed and added to your system PATH
- A Discord Bot Token
- Spotify Developer Account

### Installation

1. **Install the required packages**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**:
   - Copy `.env.example` to `.env`
   - Fill in your Discord bot token, Spotify API credentials, and Spotify playlist ID

3. **Get Spotify API Credentials**:
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
   - Create a new application
   - Note down the Client ID and Client Secret
   - Add `http://localhost:8888/callback` as a Redirect URI in your app settings

4. **Get Spotify Playlist ID**:
   - Open Spotify and go to your playlist
   - Click the three dots → Share → Copy Playlist Link
   - The ID is the string of characters after `playlist/` and before any `?`

5. **Invite the bot to your server**:
   - Go to the [Discord Developer Portal](https://discord.com/developers/applications)
   - Select your application
   - Go to the OAuth2 → URL Generator
   - Select `bot` and `applications.commands` scopes
   - Enable these bot permissions:
     - View Channels
     - Connect
     - Speak
     - Send Messages
   - Use the generated URL to add the bot to your server

### Running the Bot

```bash
python bot.py
```

### Commands

- `!play` - Start playing the Spotify playlist in your current voice channel
- `!stop` - Stop playing and disconnect the bot
- `!join` - Join a specific voice channel (or your current one)

## Hosting 24/7

For 24/7 operation, consider hosting the bot on a cloud service like:
- Replit
- Heroku
- A VPS (DigitalOcean, Linode, etc.)
- Raspberry Pi at home

## Troubleshooting

- **FFmpeg not found**: Make sure FFmpeg is installed and added to your system PATH
- **Voice connection issues**: Ensure the bot has proper permissions to join and speak in the voice channel
- **Spotify API errors**: Double-check your Spotify API credentials and playlist ID

## License

This project is open source and available under the [MIT License](LICENSE).
