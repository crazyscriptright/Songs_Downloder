# Quick Start Guide - SpotiFLAC Python

## Installation (5 minutes)

### Step 1: Install Python
Download Python 3.8+ from https://www.python.org/downloads/

### Step 2: Install FFmpeg
**Windows:**
```bash
# Download from: https://ffmpeg.org/download.html
# Add to PATH or place ffmpeg.exe in project folder
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

### Step 3: Install Dependencies
```bash
cd spotiflac-python
pip install -r requirements.txt
```

## Usage Examples

### 1. Download from Any Platform
```bash
# Spotify URL (default)
python main.py "https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp"

# Direct Tidal URL
python main.py "https://tidal.com/browse/track/123456789"

# Direct Qobuz URL
python main.py "https://www.qobuz.com/us-en/album/name/id"

# Direct Amazon Music URL
python main.py "https://music.amazon.com/albums/B08X123456"
```

### 2. Use SpotDL as Fallback (YouTube)
```bash
# Try Tidal first, fallback to SpotDL if not available
python main.py "SPOTIFY_URL" --service auto

# Force SpotDL (YouTube download)
python main.py "SPOTIFY_URL" --service spotdl

# Disable automatic fallback
python main.py "SPOTIFY_URL" --service tidal --no-fallback
```
### 3. Try Different Services
```bash
# Auto mode (tries Tidal first, then Qobuz, Amazon, SpotDL)
python main.py "SPOTIFY_URL" --service auto

# Tidal (usually best quality)
python main.py "SPOTIFY_URL" --service tidal

# Qobuz (alternative, good for classical)

# SpotDL - YouTube (last resort, lower quality)
python main.py "SPOTIFY_URL" --service spotdl
```

### 4zon Music (fallback option)
python main.py "SPOTIFY_URL" --service amazon
```

### 3. Organize Your Downloads
```bash
# Custom output folder
python main.py "SPOTIFY_URL" --output "D:\Music\FLAC"

# Custom filename with track numbers
python main.py "SPOTIFY_URL" --template "{track}. {artist} - {title}"
```

### 4. Quality Selection
```bash
# Maximum quality (default)
python main.py "SPOTIFY_URL" --quality HI_RES

# Standard lossless (smaller files)
python main.py "SPOTIFY_URL" --quality LOSSLESS

# Qobuz specific qualities
python main.py "SPOTIFY_URL" --service qobuz --quality 27  # 24-bit Hi-Res
python main.py "SPOTIFY_URL" --service qobuz --quality 7   # 24-bit Standard
python main.py "SPOTIFY_URL" --service qobuz --quality 6   # 16-bit CD
```

## Troubleshooting

### "SpotDL not found"
- Install SpotDL: `pip install spotdl`
- Or disable in config.py: `SPOTDL_ENABLED = False`

### "FFmpeg not found"
- Install FFmpeg and add to system PATH
- Or place ffmpeg.exe in project folder (Windows)

### "Rate limited by API"
- Wait 15 seconds and try: `--service qobuz` or `--service spotdl`
- Some tracks may not be available on all platforms
- SpotDL (YouTube) usually has everything but lower quality

### "All APIs failed"
- Try a different service (--service qobuz or --service amazon)
- Some tracks may not be available on all platforms

### "Track not found"
- Not all Spotify tracks are available on other platforms
- Try a different service or track

## Advanced Usage

### Batch Download (Coming Soon)
For now, use a simple bash/batch script:

**Windows (batch script):**
```batch
@echo off
python main.py "TRACK_URL_1"
python main.py "TRACK_URL_2"
python main.py "TRACK_URL_3"
```

**Linux/Mac (bash script):**
```bash
#!/bin/bash
python main.py "TRACK_URL_1"
python main.py "TRACK_URL_2"
python main.py "TRACK_URL_3"
```

### Create Album Folders
```bash
python main.py "TRACK_URL" --output "./downloads/{album_artist} - {album}"
```

## Tips
Auto mode is smart** - Tries services in order: Tidal → Qobuz → Amazon → SpotDL
2. **Direct URLs work** - Paste Tidal/Qobuz/Amazon URLs directly
3. **SpotDL as last resort** - YouTube quality is lower but has almost everything  
4. **Start with Tidal** - Usually has the best availability and quality
2. **Use ISRC fallback** - If Tidal fails, Qobuz uses ISRC matching (more reliable)
3. **Organize by templates** - Use `{album_artist}/{album}/{track}. {title}` for proper organization
4. **Check existing files** - Script automatically skips if file exists
5. **FFmpeg required** - Only needed for Amazon Music (encrypted files)

## What Gets Embedded?

Every downloaded file includes:
- ✅ Track title, artist, album
- ✅ Album artist, release date
- ✅ Track/disc numbers
- ✅ Cover art (best quality from Spotify)
- ✅ ISRC code
- ✅ Copyright info (when available)

## Performance

**Typical download times:**
- Single track (FLAC, ~30-50MB): 30-60 seconds
- Includes: metadata fetch + download + embedding

**Rate limits:**
- SongLink API: Max 1 request per 7 seconds
- Download speed: Depends on API server (usually fast)

## Need Help?

Check the original SpotiFLAC project:
https://github.com/afkarxyz/SpotiFLAC

For issues with this Python version, check:
- FFmpeg installation
- Python version (3.8+)
- Internet connection
- Service availability
