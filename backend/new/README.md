# SpotiFLAC Python

Python implementation of SpotiFLAC - Download Spotify tracks in FLAC format from Tidal, Qobuz, and Amazon Music.

**No accounts required. No API keys needed.**

## Features

- ✨ Download music in lossless FLAC format from multiple platforms
- 🎵 Support for Spotify, Tidal, Qobuz, and Amazon Music URLs
- 🔄 SpotDL integration (YouTube fallback)
- 🎨 Automatic metadata and cover art embedding
- 🔄 Automatic service fallback and API rotation
- 🎯 Quality selection (Hi-Res, Lossless, 16/24-bit)
- 📝 Customizable filename templates
- 🚀 Simple CLI interface

## Installation

### Prerequisites

1. Python 3.8 or higher
2. FFmpeg (for Amazon Music decryption)

#### Install FFmpeg:

**Windows:**
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg  # Debian/Ubuntu
sudo dnf install ffmpeg  # Fedora
```

### Install SpotiFLAC Python

```bash
# Clone repository
cd spotiflac-python

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
# Spotify URL (tries Tidal first, auto-fallback enabled)
python main.py "https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp"

# Direct Tidal URL
python main.py "https://tidal.com/browse/track/123456789"

# Direct Qobuz URL  
python main.py "https://www.qobuz.com/us-en/album/name/id"

# Direct Amazon URL
python main.py "https://music.amazon.com/albums/B08X123456"

# Force specific service
python main.py "https://open.spotify.com/track/XYZ" --service qobuz

# Use SpotDL (YouTube) as fallback
python main.py "https://open.spotify.com/track/XYZ" --service spotdl
```

### Advanced Options

```bash
# Specify quality
python main.py "SPOTIFY_URL" --quality HI_RES

# Custom output directory
python main.py "SPOTIFY_URL" --output "./my_music"

# Custom filename template
python main.py "SPOTIFY_URL" --template "{track}. {artist} - {title}"

# Disable fallback (only try specified service)
python main.py "SPOTIFY_URL" --service tidal --no-fallback
```

### Filename Templates

Available placeholders:
- `{title}` - Track title
- `{artist}` - Track artist
- `{album}` - Album name
- `{album_artist}` - Album artist
- `{year}` - Release year
- `{track}` - Track number (zero-padded)
- `{disc}` - Disc number

Examples:
```bash
# Default
{artist} - {title}

# With track number
{track}. {artist} - {title}

# Full info
{artist} - {album} ({year}) - {track}. {title}
```

### Quality Options

**Tidal:**
- `HI_RES` - Hi-Res lossless (default)
- `LOSSLESS` - Standard lossless

**Qobuz:**
- `27` or `HI_RES` - 24-bit Hi-Res (up to 192kHz)
- `7` - 24-bit Standard (up to 96kHz)
- `6` or `LOSSLESS` - 16-bit CD quality

**Amazon:**
- Automatically uses highest available quality

**SpotDL (YouTube):**
- Best effort quality (usually 128-320kbps AAC)
- Use as fallback when track not available on other services

## How It Works

1. **Spotify Metadata**: Fetches track info using TOTP-authenticated Spotify API
2. **URL Conversion**: Uses SongLink API to convert Spotify URLs to service-specific URLs
3. **Download**: Fetches audio from public APIs (Tidal/Qobuz/Amazon)
4. **Metadata Embedding**: Adds Spotify metadata and cover art to downloaded files

## API Credits

This project uses public APIs provided by:

- **Tidal**: [hifi-api](https://github.com/binimum/hifi-api) and mirrors
- **Qobuz**: [dabmusic.xyz](https://dabmusic.xyz), [squid.wtf](https://squid.wtf), [jumo-dl](https://jumo-dl.pages.dev/)
- **Amazon**: afkarxyz.fun API

Special thanks to the maintainers of these services.

## Similar Projects

- [SpotiFLAC (Go)](https://github.com/afkarxyz/SpotiFLAC) - Original version with GUI
- [SpotiFLAC Next](https://github.com/spotiverse/SpotiFLAC-Next) - Hi-Res version

## Disclaimer

This project is for **educational and personal use only**. The developer does not condone or encourage copyright infringement.

You are solely responsible for ensuring your use complies with local laws and the Terms of Service of respective platforms.

The software is provided "as is", without warranty of any kind.

## License

Educational purposes only. See original [SpotiFLAC](https://github.com/afkarxyz/SpotiFLAC) project for more information.
