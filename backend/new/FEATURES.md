# New Features Added to SpotiFLAC Python

## Summary

SpotiFLAC Python now supports:
1. ✅ **Direct URLs from Tidal, Qobuz, and Amazon Music**
2. ✅ **SpotDL integration as fallback (YouTube downloads)**
3. ✅ **Automatic service fallback**
4. ✅ **Smart URL detection**

---

## Feature 1: Direct Platform URLs

You can now paste URLs directly from any supported platform:

### Supported URL Formats

**Spotify:**
```
https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp
spotify:track:3n3Ppam7vgaVa1iaRUc9Lp
```

**Tidal:**
```
https://tidal.com/browse/track/123456789
https://listen.tidal.com/track/123456789
```

**Qobuz:**
```
https://www.qobuz.com/us-en/album/name/id
https://play.qobuz.com/album/id
```

**Amazon Music:**
```
https://music.amazon.com/albums/B08X123456
https://www.amazon.com/music/player/albums/B08X123456
```

### How It Works

```bash
# The tool auto-detects the platform
python main.py "https://tidal.com/browse/track/123456789"
# → Downloads directly from Tidal

python main.py "https://www.qobuz.com/album/xyz"
# → Downloads directly from Qobuz
```

**Benefits:**
- No need to find Spotify URL first
- Direct download from your preferred service
- Faster when you already have the URL

---

## Feature 2: SpotDL Integration (YouTube Fallback)

SpotDL is now integrated as a fallback option that downloads from YouTube.

### Installation

```bash
pip install spotdl
```

### Usage

**As fallback (automatic):**
```bash
# Tries: Tidal → Qobuz → Amazon → SpotDL
python main.py "SPOTIFY_URL" --service auto
```

**Force SpotDL:**
```bash
# Download directly from YouTube
python main.py "SPOTIFY_URL" --service spotdl
```

**Disable SpotDL:**
Edit `config.py`:
```python
SPOTDL_ENABLED = False
```

### When to Use SpotDL

✅ **Use SpotDL when:**
- Track not available on Tidal/Qobuz/Amazon
- You want guaranteed availability (YouTube has everything)
- Lossless quality not critical

⚠️ **Limitations:**
- Lower quality (YouTube AAC 128-320kbps max)
- Not true lossless
- May have slightly different audio source

---

## Feature 3: Automatic Service Fallback

The tool now tries multiple services automatically if one fails.

### How It Works

```bash
# Auto mode with fallback
python main.py "SPOTIFY_URL" --service auto

# Fallback order:
# 1. Tidal (Hi-Res FLAC)
# 2. Qobuz (Hi-Res FLAC)  
# 3. Amazon Music (FLAC)
# 4. SpotDL (YouTube AAC) - if installed
```

### Disable Fallback

```bash
# Only try specified service
python main.py "SPOTIFY_URL" --service tidal --no-fallback
```

### Example Output

```
Trying Tidal...
✗ Tidal failed: Track not found

Trying Qobuz...
✓ Qobuz download successful!
```

---

## Feature 4: Smart URL Detection

The tool automatically detects which platform a URL belongs to.

### Implemented in `url_detector.py`

```python
from modules.url_detector import URLDetector

detector = URLDetector()
platform, track_id = detector.get_track_id(url)

# Returns:
# ('spotify', '3n3Ppam7vgaVa1iaRUc9Lp')
# ('tidal', '123456789')
# ('qobuz', 'abc123xyz')
# ('amazon', 'B08X123456')
```

**Supported patterns:**
- Spotify: `/track/`, `spotify:track:`
- Tidal: `/track/`, `/browse/track/`
- Qobuz: `/album/`, `/track/`  
- Amazon: ASIN pattern `B[0-9A-Z]{9}`

---

## Updated Command Options

### New `--service` Values

```bash
--service auto      # Smart fallback (default)
--service tidal     # Force Tidal
--service qobuz     # Force Qobuz
--service amazon    # Force Amazon
--service spotdl    # Force YouTube (SpotDL)
```

### New Flag

```bash
--fallback          # Enable fallback (default)
--no-fallback       # Disable fallback
```

---

## Usage Examples

### Example 1: Auto Mode (Recommended)
```bash
python main.py "https://open.spotify.com/track/XYZ"
# Tries all services until one works
```

### Example 2: Direct Tidal Download
```bash
python main.py "https://tidal.com/browse/track/123456789"
# Downloads directly from Tidal
```

### Example 3: Force SpotDL
```bash
python main.py "https://open.spotify.com/track/XYZ" --service spotdl
# Uses YouTube as source
```

### Example 4: No Fallback
```bash
python main.py "SPOTIFY_URL" --service tidal --no-fallback
# Only tries Tidal, fails if unavailable
```

### Example 5: Quality Selection
```bash
python main.py "SPOTIFY_URL" --service qobuz --quality 27
# Qobuz 24-bit Hi-Res with auto-fallback
```

---

## File Structure Changes

### New Files
```
modules/
├── url_detector.py    # URL platform detection
└── spotdl.py          # SpotDL integration
```

### Modified Files
```
config.py              # Added SpotDL settings
main.py                # Added multi-platform support
requirements.txt       # Added spotdl dependency
README.md              # Updated documentation
QUICKSTART.md          # Updated examples
```

---

## Installation

### Update Dependencies
```bash
pip install -r requirements.txt
```

This installs:
- `spotdl>=4.2.0` (YouTube downloads)
- All previous dependencies

### Optional: Disable SpotDL
If you don't want YouTube fallback:

**config.py:**
```python
SPOTDL_ENABLED = False
```

---

## Comparison: Services

| Service | Quality | Availability | Speed | Notes |
|---------|---------|--------------|-------|-------|
| **Tidal** | ⭐⭐⭐⭐⭐ Hi-Res | ⭐⭐⭐⭐ Good | ⭐⭐⭐⭐ Fast | Best for mainstream |
| **Qobuz** | ⭐⭐⭐⭐⭐ Hi-Res | ⭐⭐⭐ Medium | ⭐⭐⭐⭐ Fast | Best for classical |
| **Amazon** | ⭐⭐⭐⭐ FLAC | ⭐⭐⭐ Medium | ⭐⭐⭐ Medium | Requires FFmpeg |
| **SpotDL** | ⭐⭐ AAC | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Medium | YouTube source |

---

## Testing

### Test URL Detection
```bash
python -c "from modules.url_detector import URLDetector; d = URLDetector(); print(d.get_track_id('YOUR_URL'))"
```

### Test SpotDL
```bash
python -c "from modules.spotdl import SpotDLDownloader; d = SpotDLDownloader()"
```

### Full Test
```bash
python example.py
```

---

## Troubleshooting

### SpotDL Issues
```bash
# Install SpotDL
pip install spotdl

# Test installation
spotdl --version

# If fails, disable in config.py
SPOTDL_ENABLED = False
```

### URL Detection Issues
```bash
# Test which platform is detected
python modules/url_detector.py
```

### Fallback Not Working
```bash
# Make sure fallback is enabled (default)
python main.py "URL" --service auto --fallback
```

---

## Migration Guide

### Old Usage
```bash
# Before (Spotify URLs only)
python main.py "https://open.spotify.com/track/XYZ" --service tidal
```

### New Usage (Backward Compatible)
```bash
# Still works the same way
python main.py "https://open.spotify.com/track/XYZ" --service tidal

# New: Direct platform URLs
python main.py "https://tidal.com/browse/track/123" --service auto

# New: YouTube fallback
python main.py "https://open.spotify.com/track/XYZ" --service spotdl
```

All existing commands still work! The changes are additions, not breaking changes.

---

## Summary of Benefits

✅ **More flexible** - Accept URLs from any platform
✅ **More reliable** - Automatic fallback to other services
✅ **Better availability** - SpotDL (YouTube) as last resort
✅ **Smarter** - Auto-detects platform and selects best service
✅ **Backward compatible** - Old commands still work

---

Enjoy the enhanced SpotiFLAC Python! 🎵
