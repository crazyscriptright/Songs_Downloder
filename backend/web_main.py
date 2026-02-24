"""
Universal Music Downloader - Flask Web Interface
"""

from flask import Flask, render_template, request, jsonify, send_file, make_response
from flask_cors import CORS
import threading
import os
import json
import re
import hashlib
from datetime import datetime
import requests
from io import BytesIO
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

try:
    from ytmusic_dynamic_tokens import YouTubeMusicAPI
    from ytmusic_dynamic_video_tokens import YouTubeMusicVideoAPI
    from jiosaavn_search import JioSaavnAPI
    import soundcloud
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"⚠ Import Error: {e}")
    print("Make sure all required modules are in the same directory!")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5000').split(',')
CORS(app, resources={
    r"/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

if os.getenv('DYNO'):
    app.config['DOWNLOAD_FOLDER'] = '/tmp/downloads'
else:
    app.config['DOWNLOAD_FOLDER'] = os.path.join(os.path.expanduser("~"), "Downloads", "Music")

os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

def cleanup_tmp_directory():
    """Clean up /tmp directory when it's getting full (Heroku has limited space)"""
    if not os.getenv('DYNO'):
        return

    try:
        tmp_dir = '/tmp'

        import shutil
        total, used, free = shutil.disk_usage(tmp_dir)
        usage_percent = (used / total) * 100

        if usage_percent > 80:
            print(f"⚠️ /tmp is {usage_percent:.1f}% full, cleaning up...")

            files_to_delete = []
            for root, dirs, files in os.walk(tmp_dir):
                for file in files:
                    file_path = os.path.join(root, file)

                    if not file.endswith('.json'):
                        try:
                            files_to_delete.append(file_path)
                        except:
                            pass

            files_to_delete.sort(key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0)

            deleted_count = 0
            for file_path in files_to_delete:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        deleted_count += 1
                except Exception as e:
                    pass

            for root, dirs, files in os.walk(tmp_dir, topdown=False):
                for name in dirs:
                    try:
                        os.rmdir(os.path.join(root, name))
                    except OSError:
                        pass

            print(f"✅ Cleaned up {deleted_count} old files from /tmp")

            total, used, free = shutil.disk_usage(tmp_dir)
            new_usage = (used / total) * 100
            print(f"📊 /tmp usage: {new_usage:.1f}% (freed {usage_percent - new_usage:.1f}%)")

    except Exception as e:
        print(f"⚠️ Error cleaning /tmp: {e}")

ytmusic_api = None
ytvideo_api = None
jiosaavn_api = None

search_results = {}
download_status = {}
active_processes = {}

if os.getenv('DYNO'):
    CACHE_DIR = '/tmp'
else:
    CACHE_DIR = '.'

UNIFIED_CACHE_FILE = os.path.join(CACHE_DIR, "music_api_cache.json")
DOWNLOAD_QUEUE_FILE = os.path.join(CACHE_DIR, "download_queue.json")
DOWNLOAD_STATUS_FILE = os.path.join(CACHE_DIR, "download_status.json")

def get_apis():
    """Initialize APIs with unified cache and headless mode"""
    global ytmusic_api, ytvideo_api, jiosaavn_api

    headless_mode = True

    if not ytmusic_api:
        ytmusic_api = YouTubeMusicAPI(
            cache_file=UNIFIED_CACHE_FILE,
            cache_duration_hours=2,
            headless=headless_mode
        )
    if not ytvideo_api:
        ytvideo_api = YouTubeMusicVideoAPI(
            cache_file=UNIFIED_CACHE_FILE,
            cache_duration_hours=2,
            headless=headless_mode
        )
    if not jiosaavn_api:
        jiosaavn_api = JioSaavnAPI()

    return ytmusic_api, ytvideo_api, jiosaavn_api

def load_persistent_data():
    """Load download status if available (from /tmp on Heroku)"""
    global download_status
    try:
        if os.path.exists(DOWNLOAD_STATUS_FILE):
            with open(DOWNLOAD_STATUS_FILE, 'r') as f:
                download_status = json.load(f)
            print(f"✅ Loaded {len(download_status)} download records")
    except (IOError, OSError, json.JSONDecodeError) as e:
        print(f"⚠ Could not load download status: {e}")
        download_status = {}

def save_download_status():
    """Save download status (only in /tmp on Heroku)"""
    try:
        with open(DOWNLOAD_STATUS_FILE, 'w') as f:
            json.dump(download_status, f, indent=2)
    except (IOError, OSError, PermissionError) as e:

        print(f"Warning: Could not save download status: {e}")
        pass

def cleanup_old_downloads():
    """Clean up old downloads"""
    try:
        current_time = datetime.now()
        to_remove = []

        for download_id, status in download_status.items():
            if 'timestamp' in status:
                download_time = datetime.fromisoformat(status['timestamp'])
                if (current_time - download_time).total_seconds() > 86400:
                    if status.get('status') in ['complete', 'error', 'cancelled']:
                        to_remove.append(download_id)

        for download_id in to_remove:
            del download_status[download_id]

        if to_remove:
            save_download_status()

    except Exception as e:
        print(f"Warning: Could not cleanup old downloads: {e}")

def search_ytmusic(query):
    """Search YouTube Music"""
    results = []
    try:
        ytmusic, _, _ = get_apis()
        data = ytmusic.search(query, use_fresh_tokens=True, retry_on_error=True)
        songs = ytmusic.parse_search_results(data) if data else []

        for song in songs:
            results.append({
                'title': song['title'],
                'artist': song['metadata'],
                'source': 'YouTube Music',
                'url': song['url'],
                'video_id': song['video_id'],
                'thumbnail': song.get('thumbnail', f"https://img.youtube.com/vi/{song['video_id']}/mqdefault.jpg"),
                'type': 'song'
            })
    except Exception as e:
        print(f"YT Music error: {e}")

    return results

def search_ytvideo(query):
    """Search YouTube Music for videos"""
    results = []
    try:
        _, ytvideo, _ = get_apis()

        data = ytvideo.search_videos(query, use_fresh_tokens=True, retry_on_error=True)

        videos = ytvideo.parse_video_results(data) if data else []

        for video in videos:
            results.append({
                'title': video['title'],
                'artist': video['metadata'],
                'source': 'YouTube Video',
                'url': video['url'],
                'video_id': video['video_id'],
                'thumbnail': video.get('thumbnail', f"https://img.youtube.com/vi/{video['video_id']}/mqdefault.jpg"),
                'type': 'video'
            })
    except Exception as e:
        print(f"YT Video error: {e}")

    return results

def extract_soundcloud_metadata_with_recommendations(soundcloud_url):
    """Extract metadata from SoundCloud URL including main track and recommendations"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        if soundcloud_url.startswith("https://soundcloud.com/"):
            mobile_url = soundcloud_url.replace("https://soundcloud.com/", "https://m.soundcloud.com/")
            url = mobile_url
        else:
            url = soundcloud_url

        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        tracks_scripts = []
        for i, script in enumerate(soup.find_all("script")):
            if script.string and '"tracks":' in script.string:
                tracks_scripts.append((i, script))

        if tracks_scripts:

            tracks_scripts.sort(key=lambda x: len(x[1].string), reverse=True)
            script_index, script_tag = tracks_scripts[0]
        else:

            script_tag = None
            for script in soup.find_all("script"):
                if script.string and len(script.string) > 50000:
                    script_content = script.string.lower()
                    if any(keyword in script_content for keyword in ['soundcloud', 'track', 'audio']):
                        script_tag = script
                        break

        if not script_tag:
            return None

        try:
            data = json.loads(script_tag.string)

            tracks_data = None
            users_data = None

            initial_store = data.get("props", {}).get("pageProps", {}).get("initialStoreState", {})
            entities = initial_store.get("entities", {})
            if entities and "tracks" in entities:
                tracks_data = entities.get("tracks", {})
                users_data = entities.get("users", {})

            elif "tracks" in data:
                tracks_data = data.get("tracks", {})
                users_data = data.get("users", {})

            else:
                def find_tracks_recursive(obj):
                    if isinstance(obj, dict):
                        if "tracks" in obj and isinstance(obj["tracks"], dict):
                            tracks_obj = obj["tracks"]
                            if any(key.startswith("soundcloud:tracks") for key in tracks_obj.keys()):
                                return tracks_obj
                        for value in obj.values():
                            result = find_tracks_recursive(value)
                            if result:
                                return result
                    elif isinstance(obj, list):
                        for item in obj:
                            result = find_tracks_recursive(item)
                            if result:
                                return result
                    return None

                tracks_data = find_tracks_recursive(data)

            if not tracks_data:
                return None

            soundcloud_tracks = []
            for key, value in tracks_data.items():
                if key.startswith("soundcloud:tracks"):
                    track_data = value.get("data", {})

                    duration_ms = track_data.get('duration', 0)
                    duration_str = "0:00"

                    if duration_ms:
                        minutes = duration_ms // 60000
                        seconds = (duration_ms % 60000) // 1000
                        duration_str = f"{minutes}:{seconds:02d}"

                    plays = track_data.get('playback_count', 0)
                    likes = track_data.get('likes_count', 0)

                    artist_name = "Unknown Artist"

                    if 'user' in track_data and isinstance(track_data['user'], dict):
                        artist_name = track_data['user'].get('username', 'Unknown Artist')
                    elif 'uploader' in track_data:
                        artist_name = track_data['uploader']
                    elif 'artist' in track_data:
                        artist_name = track_data['artist']
                    else:

                        user_id = track_data.get('user_id')
                        if user_id and users_data:

                            user_key = f"soundcloud:users:{user_id}"
                            if user_key in users_data:
                                user_info = users_data[user_key].get('data', {})
                                artist_name = user_info.get('username', user_info.get('display_name', 'Unknown Artist'))
                            else:

                                for key, user_data in users_data.items():
                                    if key.startswith("soundcloud:users:"):
                                        user_info = user_data.get('data', {})
                                        if user_info.get('id') == user_id:
                                            artist_name = user_info.get('username', user_info.get('display_name', 'Unknown Artist'))
                                            break

                    soundcloud_tracks.append({
                        'title': track_data.get('title', 'Unknown Title'),
                        'artist': artist_name,
                        'url': track_data.get('permalink_url', soundcloud_url),
                        'thumbnail': track_data.get('artwork_url', ''),
                        'duration': duration_str,
                        'plays': plays,
                        'likes': likes,
                        'genre': track_data.get('genre', ''),
                        'created_at': track_data.get('created_at', ''),
                        'source': 'SoundCloud'
                    })

            if soundcloud_tracks:
                return {
                    'main_track': soundcloud_tracks[0] if soundcloud_tracks else None,
                    'recommended_tracks': soundcloud_tracks[1:] if len(soundcloud_tracks) > 1 else [],
                    'total_tracks': len(soundcloud_tracks)
                }

        except json.JSONDecodeError:
            return None
        except Exception:
            return None

    except Exception as e:
        print(f"SoundCloud metadata extraction error: {e}")
        return None

def extract_jiosaavn_metadata(jiosaavn_url):
    """Extract metadata from JioSaavn URL using web scraping"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(jiosaavn_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        metadata = {}

        img_element = soup.find("img", {"id": "songHeaderImage"})
        if img_element:
            metadata['thumbnail'] = img_element.get("src")

        song_title_element = soup.find("h1", class_="u-h2 u-margin-bottom-tiny@sm")
        if song_title_element:
            song_title = song_title_element.get_text(strip=True)

            if song_title.endswith("Lyrics"):
                song_title = song_title[:-6].strip()
            metadata['title'] = song_title

        album_para = soup.find("p", class_="u-color-js-gray u-ellipsis@lg u-margin-bottom-tiny@sm")
        if album_para:

            album_link = album_para.find("a", {"screen_name": "song_screen", "href": lambda x: x and "/album/" in x})
            if album_link:
                metadata['album'] = album_link.get_text(strip=True)

            artist_links = album_para.find_all("a", {"screen_name": "song_screen", "href": lambda x: x and "/artist/" in x})
            artists = []
            for link in artist_links:
                artist_name = link.get_text(strip=True)
                if artist_name:
                    artists.append(artist_name)

            if artists:
                metadata['artist'] = ", ".join(artists)

        pid_value = None

        script_tags = soup.find_all("script")
        for script in script_tags:
            if script.string and '"pid"' in script.string:
                try:

                    pid_match = re.search(r'"pid"\s*:\s*"([^"]+)"', script.string)
                    if pid_match:
                        pid_value = pid_match.group(1)
                        break
                    else:

                        pid_match = re.search(r"'pid'\s*:\s*'([^']+)'", script.string)
                        if pid_match:
                            pid_value = pid_match.group(1)
                            break
                except Exception:
                    continue

        if not pid_value:
            page_content = response.text
            pid_match = re.search(r'"pid"\s*:\s*"([^"]+)"', page_content)
            if pid_match:
                pid_value = pid_match.group(1)
            else:

                pid_match = re.search(r"'pid'\s*:\s*'([^']+)'", page_content)
                if pid_match:
                    pid_value = pid_match.group(1)

        if pid_value:
            metadata['pid'] = pid_value

        language_value = None

        for script in script_tags:
            if script.string and '"language"' in script.string:
                try:

                    language_match = re.search(r'"language"\s*:\s*"([^"]+)"', script.string)
                    if language_match:
                        language_value = language_match.group(1)
                        break
                    else:

                        language_match = re.search(r"'language'\s*:\s*'([^']+)'", script.string)
                        if language_match:
                            language_value = language_match.group(1)
                            break
                except Exception:
                    continue

        if not language_value:
            page_content = response.text
            language_match = re.search(r'"language"\s*:\s*"([^"]+)"', page_content)
            if language_match:
                language_value = language_match.group(1)
            else:

                language_match = re.search(r"'language'\s*:\s*'([^']+)'", page_content)
                if language_match:
                    language_value = language_match.group(1)

        if not language_value:

            if 'english' in jiosaavn_url.lower() or 'english' in response.text.lower():
                language_value = 'english'
            elif 'hindi' in jiosaavn_url.lower() or 'hindi' in response.text.lower():
                language_value = 'hindi'
            elif 'tamil' in jiosaavn_url.lower() or 'tamil' in response.text.lower():
                language_value = 'tamil'
            elif 'telugu' in jiosaavn_url.lower() or 'telugu' in response.text.lower():
                language_value = 'telugu'
            elif 'punjabi' in jiosaavn_url.lower() or 'punjabi' in response.text.lower():
                language_value = 'punjabi'

        if language_value:
            metadata['language'] = language_value
        else:

            metadata['language'] = 'hindi'

        return metadata

    except Exception as e:
        print(f"JioSaavn metadata extraction error: {e}")
        return None

def search_jiosaavn(query):
    """Search JioSaavn"""
    results = []
    try:
        _, _, jiosaavn = get_apis()

        data = jiosaavn.search_songs(query)
        songs = jiosaavn.parse_results(data) if data else []

        for song in songs:
            artist = (
                song.get('primary_artists') or
                song.get('singers') or
                song.get('subtitle', '').split(' - ')[0] if ' - ' in song.get('subtitle', '') else
                'Unknown Artist'
            )

            results.append({
                'title': song['title'],
                'artist': artist,
                'subtitle': song.get('subtitle', ''),
                'source': 'JioSaavn',
                'url': song['perma_url'],
                'song_id': song['id'],
                'thumbnail': song.get('image', ''),
                'year': song.get('year', ''),
                'language': song.get('language', ''),
                'play_count': song.get('play_count', ''),
                'type': 'song'
            })
    except Exception as e:
        print(f"JioSaavn error: {e}")
        import traceback
        traceback.print_exc()

    return results

def search_soundcloud(query):
    """Search SoundCloud with unified cache"""
    results = []
    try:
        tracks = soundcloud.soundcloud_search(query, limit=20)

        for track in tracks:
            duration_ms = track.get('duration_ms', 0)
            if duration_ms:
                duration = f"{duration_ms // 60000}:{(duration_ms % 60000) // 1000:02d}"
            else:
                duration = "0:00"

            artwork_url = track.get('artwork_url', '')
            if artwork_url:
                artwork_url = artwork_url.replace('-large.', '-t500x500.')

            results.append({
                'title': track.get('title', 'Unknown'),
                'artist': track.get('uploader', 'Unknown Artist'),
                'source': 'SoundCloud',
                'url': track.get('url', ''),
                'thumbnail': artwork_url,
                'duration': duration,
                'track_id': track.get('id', ''),
                'plays': track.get('playback_count', 0),
                'likes': track.get('likes_count', 0),
                'genre': track.get('genre', ''),
                'type': 'song'
            })
    except Exception as e:
        print(f"SoundCloud error: {e}")
        import traceback
        traceback.print_exc()

    return results

def is_url(query):
    """Check if query is a MUSIC-related URL (not just any URL)"""
    music_url_patterns = [
        r'youtube\.com/watch',
        r'youtu\.be/',
        r'music\.youtube\.com',
        r'jiosaavn\.com/',
        r'saavn\.com/',
        r'soundcloud\.com/',
        r'spotify\.com/',
        r'gaana\.com/',
        r'wynk\.in/',
    ]
    return any(re.search(pattern, query, re.IGNORECASE) for pattern in music_url_patterns)

def validate_url_simple(url):
    """Simple URL validation - just check if it's a supported platform"""
    supported_patterns = [
        r'youtube\.com/watch',
        r'youtu\.be/',
        r'music\.youtube\.com',
        r'soundcloud\.com/',
        r'jiosaavn\.com/',
        r'saavn\.com/',
        r'spotify\.com/',
    ]

    for pattern in supported_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            if 'soundcloud.com' in url.lower():
                source = "SoundCloud"
            elif 'jiosaavn.com' in url.lower() or 'saavn.com' in url.lower():
                source = "JioSaavn"
            elif 'spotify.com' in url.lower():
                source = "Spotify"
            else:
                source = "YouTube"

            is_playlist = bool(re.search(r'[?&]list=([^&]+)', url))
            playlist_id = None
            if is_playlist:
                playlist_match = re.search(r'[?&]list=([^&]+)', url)
                if playlist_match:
                    playlist_id = playlist_match.group(1)

            return {
                'is_valid': True,
                'url': url,
                'source': source,
                'type': 'direct_url',
                'is_playlist': is_playlist,
                'playlist_id': playlist_id
            }

    return {
        'is_valid': False,
        'error': 'Unsupported URL - Only YouTube, SoundCloud, JioSaavn, and Spotify are supported',
        'url': url
    }

def extract_video_id_from_url(url):
    """Extract video ID from YouTube URLs"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def search_all_sources(query, search_id, search_type='music'):
    """Search all sources in parallel or validate and process URL"""
    global search_results

    all_results = {
        'ytmusic': [],
        'ytvideo': [],
        'jiosaavn': [],
        'soundcloud': [],
        'direct_url': [],
        'status': 'searching',
        'query_type': 'url' if is_url(query) else 'search'
    }

    if is_url(query):

        all_results['status'] = 'validating'
        search_results[search_id] = all_results

        video_info = validate_url_simple(query)

        if video_info and video_info.get('is_valid'):
            all_results['direct_url'] = [video_info]
            all_results['status'] = 'complete'
            all_results['message'] = 'Valid URL - Ready to download'
        else:
            all_results['status'] = 'error'
            all_results['error'] = video_info.get('error', 'Invalid URL')
            all_results['message'] = f"Unable to process URL: {video_info.get('error', 'Unknown error')}"

        all_results['timestamp'] = datetime.now().isoformat()
        search_results[search_id] = all_results
        return all_results

    threads = []
    results_lock = threading.Lock()

    def search_and_store(source_name, search_func):
        try:
            results = search_func(query)
            with results_lock:
                all_results[source_name] = results
        except Exception as e:
            print(f"Error searching {source_name}: {e}")

    if search_type == 'music':

        t1 = threading.Thread(target=search_and_store, args=('ytmusic', search_ytmusic))
        t3 = threading.Thread(target=search_and_store, args=('jiosaavn', search_jiosaavn))
        t4 = threading.Thread(target=search_and_store, args=('soundcloud', search_soundcloud))
        threads = [t1, t3, t4]
    elif search_type == 'video':

        t2 = threading.Thread(target=search_and_store, args=('ytvideo', search_ytvideo))
        threads = [t2]
    else:

        t1 = threading.Thread(target=search_and_store, args=('ytmusic', search_ytmusic))
        t2 = threading.Thread(target=search_and_store, args=('ytvideo', search_ytvideo))
        t3 = threading.Thread(target=search_and_store, args=('jiosaavn', search_jiosaavn))
        t4 = threading.Thread(target=search_and_store, args=('soundcloud', search_soundcloud))
        threads = [t1, t2, t3, t4]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    all_results['status'] = 'complete'
    all_results['timestamp'] = datetime.now().isoformat()

    search_results[search_id] = all_results

    return all_results

def download_song(url, title, download_id, advanced_options=None):
    """Download song/video using yt-dlp with optional advanced parameters and progress tracking"""
    global download_status, active_processes

    cleanup_tmp_directory()

    download_status[download_id] = {
        'status': 'downloading',
        'progress': 0,
        'title': title,
        'url': url,
        'eta': 'Calculating...',
        'speed': '0 KB/s',
        'timestamp': datetime.now().isoformat(),
        'advanced_options': advanced_options
    }
    save_download_status()

    try:
        import subprocess
        import re as regex
        import shlex

        if not url or not isinstance(url, str):
            raise ValueError("Invalid URL")

        if not url.startswith(('http://', 'https://')):
            raise ValueError("Only HTTP/HTTPS URLs are allowed")

        DANGEROUS_CHARS_TITLE = ['&&', '||', ';', '|', '`', '$', '<', '>', '\n', '\r']
        for dangerous_char in DANGEROUS_CHARS_TITLE:
            if dangerous_char in title:
                raise ValueError(f"Security: Dangerous character '{dangerous_char}' detected in title")

        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)

        cmd = ['yt-dlp']

        ALLOWED_AUDIO_FORMATS = ['mp3', 'm4a', 'opus', 'vorbis', 'wav', 'flac']

        ALLOWED_QUALITIES = ['0', '2', '5', '9']

        if advanced_options:
            audio_format = advanced_options.get('audioFormat', 'mp3')
            audio_quality = advanced_options.get('audioQuality', '0')
            embed_thumbnail = advanced_options.get('embedThumbnail', True)
            add_metadata = advanced_options.get('addMetadata', True)
            embed_subtitles = advanced_options.get('embedSubtitles', False)
            keep_video = advanced_options.get('keepVideo', False)
            custom_args = advanced_options.get('customArgs', '')

            video_quality = advanced_options.get('videoQuality', '1080')
            video_fps = advanced_options.get('videoFPS', '30')
            video_format = advanced_options.get('videoFormat', 'mkv')

            if audio_format not in ALLOWED_AUDIO_FORMATS:
                audio_format = 'mp3'

            if audio_quality not in ALLOWED_QUALITIES:
                audio_quality = '0'

            ALLOWED_VIDEO_FORMATS = ['mkv', 'mp4', 'webm']
            if video_format not in ALLOWED_VIDEO_FORMATS:
                video_format = 'mkv'

            if keep_video:

                if video_quality == 'best':
                    format_selector = 'bestvideo+bestaudio/best'
                else:

                    if video_fps == '60':
                        format_selector = f'bestvideo[height<={video_quality}][fps<=60]+bestaudio/best[height<={video_quality}]'
                    elif video_fps == '30':
                        format_selector = f'bestvideo[height<={video_quality}][fps<=30]+bestaudio/best[height<={video_quality}]'
                    else:
                        format_selector = f'bestvideo[height<={video_quality}]+bestaudio/best[height<={video_quality}]'

                cmd.extend([
                    '-f', format_selector,
                    '--merge-output-format', video_format,
                ])

                if embed_subtitles:
                    cmd.extend([
                        '--embed-subs',
                        '--write-auto-subs',
                        '--sub-langs', 'en.*,hi.*,all',
                    ])

                output_template = os.path.join(app.config['DOWNLOAD_FOLDER'], f"%(title)s.%(ext)s")
            else:

                cmd.extend([
                    '-x',
                    '--audio-format', audio_format,
                    '--audio-quality', audio_quality,
                ])
                output_template = os.path.join(app.config['DOWNLOAD_FOLDER'], f"%(title)s.%(ext)s")

            if add_metadata:
                cmd.append('--embed-metadata')

            if embed_thumbnail and not keep_video:
                cmd.append('--embed-thumbnail')

            if custom_args:

                DANGEROUS_CHARS_ARGS = ['&&', '||', ';', '|', '`', '$', '\n', '\r']
                for dangerous_char in DANGEROUS_CHARS_ARGS:
                    if dangerous_char in custom_args:

                        custom_args = ''
                        break

                if custom_args:

                    SAFE_ARGS = [

                        '--geo-bypass',
                        '--geo-bypass-country',
                        '--prefer-free-formats',

                        '--no-playlist',
                        '--yes-playlist',
                        '--playlist-items',
                        '--playlist-start',
                        '--playlist-end',
                        '--max-downloads',

                        '--windows-filenames',
                        '--format-sort',
                        '--prefer-free-formats',

                        '--max-filesize',
                        '--min-filesize',
                        '--limit-rate',
                        '--throttled-rate',

                        '--retries',
                        '--fragment-retries',
                        '--skip-unavailable-fragments',
                        '--abort-on-unavailable-fragment',
                        '--keep-fragments',

                        '--write-subs',
                        '--write-auto-subs',
                        '--sub-langs',
                        '--sub-format',
                        '--convert-subs',

                        '--add-chapters',
                        '--split-chapters',
                        '--no-embed-chapters',
                        '--xattrs',
                        '--concat-playlist',

                        '--no-overwrites',
                        '--continue',
                        '--no-continue',
                        '--no-part',
                        '--no-mtime',
                        '--write-description',
                        '--write-info-json',
                        '--write-playlist-metafiles',

                        '--encoding',
                        '--legacy-server-connect',
                        '--no-check-certificates',
                        '--prefer-insecure',
                        '--add-header',
                        '--sleep-requests',
                        '--sleep-interval',
                        '--max-sleep-interval',
                        '--sleep-subtitles',
                    ]

                    try:
                        parsed_args = shlex.split(custom_args)
                        for arg in parsed_args:

                            has_danger = any(dc in arg for dc in DANGEROUS_CHARS_ARGS)
                            if has_danger:

                                continue

                            arg_name = arg.split('=')[0] if '=' in arg else arg
                            if arg_name in SAFE_ARGS:
                                cmd.append(arg)

                    except Exception as e:

                        pass
        else:

            cmd.extend([
                '--audio-format', 'mp3',
                '-x',
                '--audio-quality', '0',
                '--embed-metadata',
                '--embed-thumbnail',
            ])
            output_template = os.path.join(app.config['DOWNLOAD_FOLDER'], f"%(title)s.%(ext)s")

        download_dir = os.path.join(app.config['DOWNLOAD_FOLDER'], download_id)
        os.makedirs(download_dir, exist_ok=True)

        cmd.extend([
            '-P', download_dir,
            '-o', '%(title)s.%(ext)s',
            '--newline',
            url
        ])

        creation_flags = 0
        if os.name == 'nt':
            creation_flags = subprocess.BELOW_NORMAL_PRIORITY_CLASS

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            shell=False,
            creationflags=creation_flags
        )

        active_processes[download_id] = process

        if os.name != 'nt':
            try:
                import resource
                os.setpriority(os.PRIO_PROCESS, process.pid, 10)
            except Exception as e:
                pass

        error_messages = []
        has_progress = False

        for line in process.stdout:

            if download_status.get(download_id, {}).get('status') == 'cancelled':
                print(f"🚫 Download {download_id} was cancelled")
                process.terminate()
                break

            line = line.strip()

            if 'ERROR:' in line:
                error_msg = line.replace('ERROR:', '').strip()
                error_messages.append(error_msg)

            error_patterns = [
                'Video unavailable',
                'Private video',
                'This video is not available',
                'Unable to download',
                'HTTP Error',
                'is not a valid URL',
                'Unsupported URL',
                'Video is not available',
                'This video has been removed',
                'no suitable formats',
                'Requested format is not available',
                'Sign in to confirm',
                'members-only content',
            ]

            if any(pattern.lower() in line.lower() for pattern in error_patterns):
                error_messages.append(line)

            if '[download]' in line and '%' in line:
                has_progress = True
                try:

                    percent_match = regex.search(r'(\d+\.?\d*)%', line)
                    if percent_match:
                        progress = float(percent_match.group(1))

                        speed_match = regex.search(r'at\s+([\d\.]+\s*[KMG]iB/s)', line)
                        speed = speed_match.group(1) if speed_match else 'Unknown'

                        eta_match = regex.search(r'ETA\s+([\d:]+)', line)
                        eta = eta_match.group(1) if eta_match else 'Unknown'

                        download_status[download_id] = {
                            'status': 'downloading',
                            'progress': min(progress, 99),
                            'title': title,
                            'url': url,
                            'speed': speed,
                            'eta': eta,
                            'timestamp': download_status[download_id]['timestamp'],
                            'advanced_options': advanced_options
                        }
                        save_download_status()
                except Exception as parse_err:

                    pass

        if download_id in active_processes:
            del active_processes[download_id]

        process.wait()

        if download_status.get(download_id, {}).get('status') == 'cancelled':
            return

        if error_messages:

            error_text = ' | '.join(error_messages[:3])
            download_status[download_id] = {
                'status': 'error',
                'progress': 0,
                'title': title,
                'url': url,
                'error': error_text,
                'speed': '0 KB/s',
                'eta': 'N/A',
                'timestamp': download_status[download_id]['timestamp'],
                'failed_at': datetime.now().isoformat(),
                'advanced_options': advanced_options
            }
            save_download_status()
            return

        if process.returncode == 0 and has_progress:

            download_dir = os.path.join(app.config['DOWNLOAD_FOLDER'], download_id)
            try:
                files = os.listdir(download_dir)

                latest_file = max(
                    [os.path.join(download_dir, f) for f in files],
                    key=os.path.getctime,
                    default=None
                )
            except FileNotFoundError:
                latest_file = None

            if latest_file:
                filename = os.path.basename(latest_file)
                download_status[download_id] = {
                    'status': 'complete',
                    'progress': 100,
                    'title': title,
                    'url': url,
                    'file': filename,
                    'speed': 'Complete',
                    'eta': '0:00',
                    'timestamp': download_status[download_id]['timestamp'],
                    'completed_at': datetime.now().isoformat(),
                    'advanced_options': advanced_options
                }
            else:
                download_status[download_id] = {
                    'status': 'complete',
                    'progress': 100,
                    'title': title,
                    'url': url,
                    'file': f"{safe_title}.mp3",
                    'speed': 'Complete',
                    'eta': '0:00',
                    'timestamp': download_status[download_id]['timestamp'],
                    'completed_at': datetime.now().isoformat(),
                    'advanced_options': advanced_options
                }
        elif process.returncode == 0 and not has_progress:

            download_dir = os.path.join(app.config['DOWNLOAD_FOLDER'], download_id)
            try:
                files = os.listdir(download_dir)
                if files:

                    latest_file = max(
                        [os.path.join(download_dir, f) for f in files],
                        key=os.path.getctime,
                        default=None
                    )

                    if latest_file and (datetime.now().timestamp() - os.path.getctime(latest_file)) < 10:
                        filename = os.path.basename(latest_file)
                        download_status[download_id] = {
                            'status': 'complete',
                            'progress': 100,
                            'title': title,
                            'url': url,
                            'file': filename,
                            'speed': 'Complete',
                            'eta': '0:00',
                            'timestamp': download_status[download_id]['timestamp'],
                            'completed_at': datetime.now().isoformat(),
                            'advanced_options': advanced_options
                        }
                        save_download_status()
                        return
            except Exception:
                pass

            download_status[download_id] = {
                'status': 'error',
                'progress': 0,
                'title': title,
                'url': url,
                'error': 'No download progress detected. URL may be invalid or unavailable.',
                'speed': '0 KB/s',
                'eta': 'N/A',
                'timestamp': download_status[download_id]['timestamp'],
                'failed_at': datetime.now().isoformat(),
                'advanced_options': advanced_options
            }
        else:

            error_text = 'Download failed'
            if error_messages:
                error_text = ' | '.join(error_messages[:3])

            download_status[download_id] = {
                'status': 'error',
                'progress': 0,
                'title': title,
                'url': url,
                'error': error_text,
                'speed': '0 KB/s',
                'eta': 'N/A',
                'timestamp': download_status[download_id]['timestamp'],
                'failed_at': datetime.now().isoformat(),
                'advanced_options': advanced_options
            }

            if 'youtube.com' in url or 'youtu.be' in url:
                try:
                    download_with_proxy_api(url, title, download_id, advanced_options)
                    return
                except Exception as fallback_error:
                    print(f"❌ Fallback proxy API also failed: {fallback_error}")

    except Exception as e:
        download_status[download_id] = {
            'status': 'error',
            'progress': 0,
            'title': title,
            'url': url,
            'error': str(e),
            'speed': '0 KB/s',
            'eta': 'N/A',
            'timestamp': download_status[download_id]['timestamp'],
            'failed_at': datetime.now().isoformat(),
            'advanced_options': advanced_options
        }

    finally:

        save_download_status()

        if download_id in active_processes:
            del active_processes[download_id]

@app.route('/')
def index():
    """Render main page with optional URL parameter search"""

    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'music')

    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5000')

    return render_template('index.html',
                         initial_query=query,
                         initial_type=search_type,
                         frontend_url=frontend_url)

@app.route('/search', methods=['POST'])
def search():
    """Handle search request"""
    data = request.get_json()
    query = data.get('query', '').strip()
    search_type = data.get('type', 'music')

    if not query:
        return jsonify({'error': 'Empty query'}), 400

    search_id = f"search_{datetime.now().timestamp()}"

    query_type = 'url' if is_url(query) else 'search'

    thread = threading.Thread(
        target=search_all_sources,
        args=(query, search_id, search_type)
    )
    thread.start()

    return jsonify({
        'search_id': search_id,
        'status': 'started',
        'query_type': query_type
    })

@app.route('/search/jiosaavn', methods=['POST'])
def search_jiosaavn_endpoint():
    """Fast JioSaavn search endpoint"""
    data = request.get_json()
    query = data.get('query', '').strip()

    if not query:
        return jsonify({'error': 'Query is required'}), 400

    try:
        results = search_jiosaavn(query)
        return jsonify({
            'status': 'complete',
            'source': 'jiosaavn',
            'results': results,
            'count': len(results),
            'query': query
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'source': 'jiosaavn',
            'error': str(e),
            'results': [],
            'count': 0,
            'query': query
        })

@app.route('/search/soundcloud', methods=['POST'])
def search_soundcloud_endpoint():
    """Fast SoundCloud search endpoint"""
    data = request.get_json()
    query = data.get('query', '').strip()

    if not query:
        return jsonify({'error': 'Query is required'}), 400

    try:
        results = search_soundcloud(query)
        return jsonify({
            'status': 'complete',
            'source': 'soundcloud',
            'results': results,
            'count': len(results),
            'query': query
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'source': 'soundcloud',
            'error': str(e),
            'results': [],
            'count': 0,
            'query': query
        })

@app.route('/search/ytmusic', methods=['POST'])
def search_ytmusic_endpoint():
    """Fast YouTube Music search endpoint"""
    data = request.get_json()
    query = data.get('query', '').strip()

    if not query:
        return jsonify({'error': 'Query is required'}), 400

    try:
        results = search_ytmusic(query)
        return jsonify({
            'status': 'complete',
            'source': 'ytmusic',
            'results': results,
            'count': len(results),
            'query': query
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'source': 'ytmusic',
            'error': str(e),
            'results': [],
            'count': 0,
            'query': query
        })

@app.route('/search/ytvideo', methods=['POST'])
def search_ytvideo_endpoint():
    """Fast YouTube Video search endpoint"""
    data = request.get_json()
    query = data.get('query', '').strip()

    if not query:
        return jsonify({'error': 'Query is required'}), 400

    try:
        results = search_ytvideo(query)
        return jsonify({
            'status': 'complete',
            'source': 'ytvideo',
            'results': results,
            'count': len(results),
            'query': query
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'source': 'ytvideo',
            'error': str(e),
            'results': [],
            'count': 0,
            'query': query
        })

def get_youtube_suggestions(query):
    """Get search suggestions from YouTube API"""
    try:
        import urllib.parse
        import json

        encoded_query = urllib.parse.quote(query)
        url = f"https://suggestqueries.google.com/complete/search?client=youtube&q={encoded_query}"

        response = requests.get(url, timeout=3)
        if response.status_code == 200:

            jsonp_text = response.text
            if jsonp_text.startswith('window.google.ac.h('):
                json_text = jsonp_text[19:-1]
                data = json.loads(json_text)
                suggestions = [item[0] for item in data[1][:5]]
                return suggestions
    except Exception as e:
        print(f"YouTube suggestions error: {e}")
    return []

def get_jiosaavn_suggestions(query):
    """Get search suggestions from JioSaavn search"""
    try:

        from jiosaavn_api import search_songs

        results = search_songs(query, limit=3)
        if results and 'data' in results and 'results' in results['data']:
            suggestions = []
            for song in results['data']['results'][:3]:
                if 'title' in song:
                    title = song['title']

                    if title and len(title) > 3:
                        suggestions.append(title)
            return suggestions
    except Exception as e:
        print(f"JioSaavn suggestions error: {e}")
    return []

def get_spotify_suggestions(query):
    """Get search suggestions using Spotify-like approach"""
    try:

        suggestions = [
            f"{query} song",
            f"{query} remix",
            f"{query} cover",
            f"{query} acoustic",
            f"{query} live"
        ]
        return suggestions[:3]
    except Exception:
        return []

@app.route('/suggestions')
def get_suggestions():
    """Get dynamic search suggestions from multiple APIs"""
    query = request.args.get('q', '').strip()

    if not query or len(query) < 2:
        return jsonify({'suggestions': []})

    try:
        all_suggestions = []

        youtube_suggestions = get_youtube_suggestions(query)
        if youtube_suggestions:
            all_suggestions.extend(youtube_suggestions[:4])

        jiosaavn_suggestions = get_jiosaavn_suggestions(query)
        if jiosaavn_suggestions:
            all_suggestions.extend(jiosaavn_suggestions[:2])

        spotify_suggestions = get_spotify_suggestions(query)
        all_suggestions.extend(spotify_suggestions[:2])

        seen = set()
        unique_suggestions = []
        for suggestion in all_suggestions:
            suggestion_lower = suggestion.lower().strip()
            if suggestion_lower not in seen and len(suggestion_lower) > 1:
                seen.add(suggestion_lower)
                unique_suggestions.append(suggestion)

        final_suggestions = unique_suggestions[:6]

        return jsonify({'suggestions': final_suggestions})

    except Exception as e:
        print(f"❌ Suggestions error: {e}")

        fallback_suggestions = [
            f"{query} song",
            f"{query} music",
            f"{query} latest"
        ]
        return jsonify({'suggestions': fallback_suggestions})

@app.route('/search_status/<search_id>')
def search_status(search_id):
    """Get search status and results"""
    if search_id in search_results:
        return jsonify(search_results[search_id])
    else:
        return jsonify({'status': 'not_found'}), 404

@app.route('/download', methods=['POST'])
def download():
    """Handle download request with optional advanced options"""
    data = request.get_json()
    url = data.get('url')
    title = data.get('title')
    advanced_options = data.get('advancedOptions')

    if not url or not title:
        return jsonify({'error': 'Missing url or title'}), 400

    if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        return jsonify({'error': 'Invalid URL format. Only HTTP/HTTPS URLs are allowed.'}), 400

    DANGEROUS_CHARS_TITLE = ['&&', '||', ';', '|', '`', '$', '<', '>', '\n', '\r']
    for dangerous_char in DANGEROUS_CHARS_TITLE:
        if dangerous_char in title:
            return jsonify({'error': f'Security: Dangerous character detected in title'}), 400

    if not isinstance(title, str) or '..' in title or '/' in title or '\\' in title:
        return jsonify({'error': 'Invalid title'}), 400

    if len(title) > 200:
        title = title[:200]

    if len(url) > 2048:
        return jsonify({'error': 'URL too long'}), 400

    if advanced_options and isinstance(advanced_options, dict):
        custom_args = advanced_options.get('customArgs', '')
        if custom_args:
            DANGEROUS_CHARS_ARGS = ['&&', '||', ';', '|', '`', '$', '\n', '\r']
            for dangerous_char in DANGEROUS_CHARS_ARGS:
                if dangerous_char in custom_args:
                    return jsonify({'error': f'Security: Dangerous character detected in custom arguments'}), 400

    download_id = f"download_{datetime.now().timestamp()}"

    thread = threading.Thread(
        target=download_song,
        args=(url, title, download_id, advanced_options)
    )
    thread.start()

    return jsonify({
        'download_id': download_id,
        'status': 'started'
    })

@app.route('/download_status/<download_id>')
def download_status_check(download_id):
    """Check download status"""
    if download_id in download_status:
        status = download_status[download_id]

        if status['status'] == 'complete' and 'file' in status:
            status['download_url'] = f"/get_file/{download_id}/{status['file']}"
        return jsonify(status)
    else:
        return jsonify({'status': 'not_found'}), 404

@app.route('/downloads')
def get_all_downloads():
    """Get all download statuses for persistent tracking"""

    filtered_downloads = {}
    current_time = datetime.now()

    for download_id, status in download_status.items():

        if status.get('status') in ['downloading', 'queued', 'preparing']:
            filtered_downloads[download_id] = status
        elif status.get('status') in ['complete', 'error', 'cancelled']:

            if 'timestamp' in status:
                try:
                    download_time = datetime.fromisoformat(status['timestamp'])
                    if (current_time - download_time).total_seconds() < 86400:
                        filtered_downloads[download_id] = status
                except:

                    filtered_downloads[download_id] = status
            else:

                filtered_downloads[download_id] = status

    for download_id, status in filtered_downloads.items():
        if status['status'] == 'complete' and 'file' in status:
            status['download_url'] = f"/get_file/{download_id}/{status['file']}"

    return jsonify(filtered_downloads)

@app.route('/cancel_download/<download_id>', methods=['POST'])
def cancel_download(download_id):
    """Cancel a download"""
    global download_status, active_processes

    if download_id not in download_status:
        return jsonify({'error': 'Download not found'}), 404

    current_status = download_status[download_id]['status']

    if current_status in ['complete', 'error', 'cancelled']:
        return jsonify({'error': 'Download already finished'}), 400

    download_status[download_id]['status'] = 'cancelled'
    download_status[download_id]['cancelled_at'] = datetime.now().isoformat()
    download_status[download_id]['progress'] = 0
    download_status[download_id]['speed'] = 'Cancelled'
    download_status[download_id]['eta'] = 'N/A'

    if download_id in active_processes:
        try:
            process = active_processes[download_id]
            process.terminate()
            print(f"🚫 Terminated download process for {download_id}")
        except Exception as e:
            print(f"Warning: Could not terminate process for {download_id}: {e}")

    save_download_status()

    return jsonify({
        'status': 'cancelled',
        'message': f"Download cancelled: {download_status[download_id]['title']}"
    })

@app.route('/clear_downloads', methods=['POST'])
def clear_downloads():
    """Clear completed/failed downloads"""
    global download_status

    to_remove = []
    for download_id, status in download_status.items():
        if status.get('status') in ['complete', 'error', 'cancelled']:
            to_remove.append(download_id)

    for download_id in to_remove:
        del download_status[download_id]

    save_download_status()

    return jsonify({
        'message': f'Cleared {len(to_remove)} finished downloads',
        'cleared_count': len(to_remove)
    })

@app.route('/get_file/<download_id>/<filename>')
def get_file(download_id, filename):
    """Serve downloaded file to browser"""
    try:

        if not re.match(r'^[a-zA-Z0-9_.-]+$', download_id):
             return jsonify({'error': 'Invalid download ID'}), 400

        file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], download_id, filename)
        if os.path.exists(file_path):
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename
            )
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/preview_url', methods=['POST'])
def preview_url():
    """Get video/song info from URL using existing search APIs (FAST)"""
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'Missing URL'}), 400

    if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        return jsonify({'error': 'Invalid URL format'}), 400

    try:

        source = "Unknown"
        if 'soundcloud.com' in url.lower():
            source = "SoundCloud"
        elif 'jiosaavn.com' in url.lower() or 'saavn.com' in url.lower():
            source = "JioSaavn"
        elif 'spotify.com' in url.lower():
            source = "Spotify"
        elif 'youtube.com' in url.lower() or 'youtu.be' in url.lower() or 'music.youtube.com' in url.lower():
            source = "YouTube"

        if source == "YouTube":
            video_id = extract_video_id_from_url(url)
            if video_id:
                try:
                    ytmusic, ytvideo, _ = get_apis()

                    try:

                        yt_url = f"https://www.youtube.com/watch?v={video_id}"

                        search_data = ytvideo.search_videos(video_id, use_fresh_tokens=True, retry_on_error=False)

                        if search_data:
                            videos = ytvideo.parse_video_results(search_data)
                            if videos and len(videos) > 0:
                                video = videos[0]

                                preview_data = {
                                    'title': video.get('title', 'Unknown Title'),
                                    'uploader': video.get('metadata', 'Unknown Channel'),
                                    'channel': video.get('metadata', 'Unknown Channel'),
                                    'thumbnail': video.get('thumbnail', f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"),
                                    'video_id': video_id,
                                    'webpage_url': yt_url,
                                    'source': 'YouTube'
                                }

                                return jsonify(preview_data)
                    except Exception as e:

                        pass

                    if video_id:
                        preview_data = {
                            'title': 'YouTube Video',
                            'uploader': 'Unknown Channel',
                            'channel': 'Unknown Channel',
                            'thumbnail': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                            'video_id': video_id,
                            'webpage_url': url,
                            'source': 'YouTube'
                        }
                        return jsonify(preview_data)
                    else:

                        return jsonify({'error': 'Invalid YouTube URL - Unable to extract video information'}), 400

                except Exception as e:

                    return jsonify({'error': 'Invalid YouTube URL - Unable to extract video information'}), 400

        if source == "JioSaavn":
            enhanced_metadata = extract_jiosaavn_metadata(url)
            if enhanced_metadata:
                preview_data = {
                    'title': enhanced_metadata.get('title', f'{source} Content'),
                    'uploader': enhanced_metadata.get('artist', source),
                    'channel': enhanced_metadata.get('artist', source),
                    'thumbnail': enhanced_metadata.get('thumbnail', ''),
                    'album': enhanced_metadata.get('album', ''),
                    'pid': enhanced_metadata.get('pid', ''),
                    'language': enhanced_metadata.get('language', 'hindi'),
                    'webpage_url': url,
                    'source': source
                }
                return jsonify(preview_data)
            else:

                return jsonify({'error': 'Invalid JioSaavn URL - Unable to extract song information'}), 400

        elif source == "SoundCloud":
            enhanced_metadata = extract_soundcloud_metadata_with_recommendations(url)

            if enhanced_metadata and enhanced_metadata.get('main_track'):
                main_track = enhanced_metadata['main_track']
                preview_data = {
                    'title': main_track.get('title', f'{source} Content'),
                    'uploader': main_track.get('artist', source),
                    'channel': main_track.get('artist', source),
                    'thumbnail': main_track.get('thumbnail', ''),
                    'duration': main_track.get('duration', ''),
                    'plays': main_track.get('plays', 0),
                    'likes': main_track.get('likes', 0),
                    'genre': main_track.get('genre', ''),
                    'webpage_url': url,
                    'source': source,
                    'soundcloud_data': enhanced_metadata
                }
                return jsonify(preview_data)
            else:

                return jsonify({'error': 'Invalid SoundCloud URL - Unable to extract track information'}), 400

        return jsonify({'error': f'Invalid {source} URL - Unable to extract content information'}), 400

    except Exception as e:
        print(f"❌ Preview error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/jiosaavn_suggestions/<pid>')
def get_jiosaavn_suggestions_by_pid(pid):
    """Get JioSaavn recommendations using PID with India geo-location and Selenium fallback"""
    try:

        if not pid or not re.match(r'^[a-zA-Z0-9_-]{1,20}$', pid):
            return jsonify({'error': 'Invalid PID format'}), 400

        language = request.args.get('language', 'english')

        allowed_languages = ['english', 'hindi', 'telugu', 'tamil', 'punjabi', 'bengali', 'marathi', 'gujarati', 'kannada', 'malayalam']
        if language not in allowed_languages:
            language = 'english'

        is_heroku = os.getenv('DYNO') is not None

        suggestions = []
        method_used = 'api'

        try:
            print(f"🔄 Fetching suggestions via API for PID: {pid}")

            api_url = f"https://www.jiosaavn.com/api.php?__call=reco.getreco&api_version=4&_format=json&_marker=0&ctx=wap6dot0&pid={pid}&language={language}"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Origin": "https://www.jiosaavn.com",
                "Referer": "https://www.jiosaavn.com/",
                "X-Requested-With": "XMLHttpRequest",
                "X-Forwarded-For": "103.21.124.0",
                "CF-IPCountry": "IN"
            }

            print(f"   🌍 Using India geo-location headers")
            response = requests.get(api_url, headers=headers, timeout=10)

            print(f"   📊 Status: {response.status_code}, Size: {len(response.content)} bytes")

            if response.status_code == 200 and len(response.content) > 10:
                data = response.json()

                if isinstance(data, list) and len(data) > 0:
                    print(f"   ✅ API returned {len(data)} items")

                    for item in data:
                        if isinstance(item, dict):

                            subtitle = item.get('subtitle', '')
                            artist = subtitle.split(' - ')[0] if ' - ' in subtitle else 'Unknown Artist'

                            suggestion = {
                                'id': item.get('id', ''),
                                'title': item.get('title', ''),
                                'artist': artist,
                                'subtitle': subtitle,
                                'thumbnail': item.get('image', ''),
                                'url': item.get('perma_url', ''),
                                'duration': str(item.get('duration', 0)) if item.get('duration') else '0:00',
                                'language': item.get('language', ''),
                                'type': item.get('type', 'song'),
                                'year': item.get('year', ''),
                                'play_count': item.get('play_count', 0)
                            }
                            suggestions.append(suggestion)

                    print(f"✅ API Method Success: {len(suggestions)} suggestions")
                    method_used = 'api'
                else:
                    print(f"   ⚠️ API returned empty or invalid data")
                    if is_heroku:
                        print(f"   🌐 [HEROKU] Likely geo-blocked, will try Selenium")
            else:
                print(f"   ⚠️ API call failed or returned minimal data")

        except Exception as e:
            print(f"   ❌ API Error: {e}")

        if not suggestions:
            try:
                print(f"\n🔄 Method 2: Selenium web scraping fallback")

                from jiosaavn_suggestions_simple import JioSaavnSuggestions

                scraper = JioSaavnSuggestions()
                selenium_suggestions = scraper._try_selenium(pid, language, max_results=10)

                if selenium_suggestions:
                    suggestions = selenium_suggestions
                    method_used = 'selenium'
                    print(f"✅ Selenium Success: Got {len(suggestions)} suggestions")
                else:
                    print(f"⚠️ Selenium returned no results")

            except Exception as e:
                print(f"❌ Selenium Error: {e}")

        if suggestions and len(suggestions) > 0:
            return jsonify({
                'success': True,
                'pid': pid,
                'language': language,
                'suggestions': suggestions,
                'count': len(suggestions),
                'method': method_used
            })
        else:

            return jsonify({
                'success': False,
                'error': 'No suggestions available for this song',
                'pid': pid,
                'language': language,
                'suggestions': [],
                'count': 0,
                'method': method_used
            }), 404

    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/extract_jiosaavn_pid', methods=['POST'])
def extract_jiosaavn_pid():
    """Extract PID from JioSaavn URL"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()

        if not url:
            return jsonify({'error': 'URL is required'}), 400

        if 'jiosaavn.com' not in url and 'saavn.com' not in url:
            return jsonify({'error': 'Not a valid JioSaavn URL'}), 400

        metadata = extract_jiosaavn_metadata(url)

        if metadata and 'pid' in metadata:
            return jsonify({
                'success': True,
                'pid': metadata['pid'],
                'metadata': metadata
            })
        else:
            return jsonify({'error': 'Could not extract PID from URL'}), 404

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/proxy_image')
def proxy_image():
    """Proxy images to avoid CORS issues, with browser & in-memory caching"""
    url = request.args.get('url')
    size = request.args.get('size', 'medium')
    if not url:
        return '', 404

    try:

        cache_key = hashlib.md5(f"{url}:{size}".encode()).hexdigest()

        cached = _image_cache.get(cache_key)
        if cached:
            content_bytes, content_type = cached
        else:
            response = requests.get(url, timeout=8)
            response.raise_for_status()
            content_bytes = response.content
            content_type = response.headers.get('Content-Type', 'image/jpeg')

            if len(_image_cache) > 500:

                for k in list(_image_cache.keys())[:100]:
                    del _image_cache[k]
            _image_cache[cache_key] = (content_bytes, content_type)

        resp = make_response(send_file(
            BytesIO(content_bytes),
            mimetype=content_type
        ))

        resp.headers['Cache-Control'] = 'public, max-age=604800, stale-while-revalidate=86400'
        resp.headers['ETag'] = cache_key
        resp.headers['Vary'] = 'Accept'
        return resp
    except Exception:
        return '', 404

_image_cache: dict = {}

VIDEO_DOWNLOAD_API_KEY = os.getenv('VIDEO_DOWNLOAD_API_KEY', '')

def download_with_proxy_api(url, title, download_id, advanced_options=None):
    """Fallback download using video-download-api.com when yt-dlp fails"""
    global download_status

    try:
        print(f"🔄 Attempting fallback download via proxy API for: {title}")

        if not VIDEO_DOWNLOAD_API_KEY:
            raise Exception("Proxy API key not configured")

        download_status[download_id] = {
            'status': 'downloading',
            'progress': 0,
            'title': title,
            'url': url,
            'eta': 'Initiating proxy download...',
            'speed': '0 KB/s',
            'timestamp': download_status[download_id].get('timestamp', datetime.now().isoformat()),
            'advanced_options': advanced_options
        }
        save_download_status()

        format_type = 'mp3'
        if advanced_options:
            audio_format = advanced_options.get('audioFormat', 'mp3')
            if audio_format in ['mp3', 'm4a', 'flac', 'wav']:
                format_type = audio_format

        params = {
            'format': format_type,
            'url': url,
            'apikey': VIDEO_DOWNLOAD_API_KEY,
            'add_info': '1'
        }

        if advanced_options:
            if advanced_options.get('audioQuality'):
                params['audio_quality'] = advanced_options['audioQuality']

        api_url = 'https://p.savenow.to/ajax/download.php'
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data.get('success'):
            raise Exception(data.get('message', 'Failed to initiate download'))

        job_id = data.get('id')
        if not job_id:
            raise Exception('No job ID returned from API')

        max_attempts = 60
        attempts = 0

        while attempts < max_attempts:
            attempts += 1

            progress_url = f"https://p.savenow.to/api/progress?id={job_id}"
            progress_response = requests.get(progress_url, timeout=10)
            progress_data = progress_response.json()

            progress_percent = round((progress_data.get('progress', 0) / 1000) * 100)
            status_text = progress_data.get('text', 'Processing')

            download_status[download_id] = {
                'status': 'downloading',
                'progress': progress_percent,
                'title': title,
                'url': url,
                'eta': f'{status_text}...',
                'speed': 'Proxy API',
                'timestamp': download_status[download_id]['timestamp'],
                'advanced_options': advanced_options
            }
            save_download_status()

            if progress_data.get('success') == 1 and progress_data.get('progress') == 1000:
                download_url = progress_data.get('download_url')
                if not download_url:
                    raise Exception('No download URL in completed response')

                download_status[download_id]['eta'] = 'Downloading file...'
                save_download_status()

                file_response = requests.get(download_url, stream=True, timeout=60)
                file_response.raise_for_status()

                safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                filename = f"{safe_title}.{format_type}"

                download_dir = os.path.join(app.config['DOWNLOAD_FOLDER'], download_id)
                os.makedirs(download_dir, exist_ok=True)
                filepath = os.path.join(download_dir, filename)

                with open(filepath, 'wb') as f:
                    for chunk in file_response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                download_status[download_id] = {
                    'status': 'complete',
                    'progress': 100,
                    'title': title,
                    'url': url,
                    'file': filename,
                    'speed': 'Complete',
                    'eta': '0:00',
                    'timestamp': download_status[download_id]['timestamp'],
                    'completed_at': datetime.now().isoformat(),
                    'downloaded_via': 'proxy_api',
                    'advanced_options': advanced_options
                }
                save_download_status()

                print(f"✅ Proxy API download successful: {filename}")
                return

            import time
            time.sleep(2)

        raise Exception('Download timeout - took too long to process')

    except Exception as e:
        print(f"❌ Proxy API download failed: {e}")
        download_status[download_id] = {
            'status': 'error',
            'progress': 0,
            'title': title,
            'url': url,
            'error': f'Both yt-dlp and proxy API failed. Last error: {str(e)}',
            'speed': '0 KB/s',
            'eta': 'N/A',
            'timestamp': download_status[download_id].get('timestamp', datetime.now().isoformat()),
            'failed_at': datetime.now().isoformat(),
            'advanced_options': advanced_options
        }
        save_download_status()
        raise

@app.route('/proxy/download', methods=['GET'])
def proxy_download():
    """Proxy for video download API to avoid CORS"""
    try:
        if not VIDEO_DOWNLOAD_API_KEY:
            return jsonify({'error': 'API key not configured on server'}), 500

        params = {
            'format': request.args.get('format'),
            'url': request.args.get('url'),
            'apikey': VIDEO_DOWNLOAD_API_KEY,
            'add_info': request.args.get('add_info', '1'),
        }

        if request.args.get('audio_quality'):
            params['audio_quality'] = request.args.get('audio_quality')
        if request.args.get('allow_extended_duration'):
            params['allow_extended_duration'] = request.args.get('allow_extended_duration')
        if request.args.get('no_merge'):
            params['no_merge'] = request.args.get('no_merge')
        if request.args.get('audio_language'):
            params['audio_language'] = request.args.get('audio_language')
        if request.args.get('start_time'):
            params['start_time'] = request.args.get('start_time')
        if request.args.get('end_time'):
            params['end_time'] = request.args.get('end_time')

        api_url = 'https://p.savenow.to/ajax/download.php'
        response = requests.get(api_url, params=params)

        response_data = response.json()
        if 'message' in response_data:
            del response_data['message']

        return jsonify(response_data), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/proxy/progress', methods=['GET'])
def proxy_progress():
    """Proxy for progress check to avoid CORS"""
    try:
        job_id = request.args.get('id')

        api_url = f"https://p.savenow.to/api/progress?id={job_id}"
        response = requests.get(api_url)

        response_data = response.json()
        if 'message' in response_data:
            del response_data['message']

        return jsonify(response_data), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/proxy/file', methods=['GET'])
def proxy_file():
    """Proxy for actual file download to avoid CORS and hide original headers"""
    try:
        download_url = request.args.get('url')

        response = requests.get(download_url, stream=True, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        filename = 'download.mp3'
        if 'Content-Disposition' in response.headers:
            content_disposition = response.headers['Content-Disposition']
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"')

        content_type = response.headers.get('Content-Type', 'application/octet-stream')

        return app.response_class(
            response.iter_content(chunk_size=8192),
            mimetype=content_type,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': response.headers.get('Content-Length', ''),
                'Cache-Control': 'no-cache',
                'X-Content-Type-Options': 'nosniff'
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🎵 Universal Music Downloader")
    print(f"📁 Downloads: {app.config['DOWNLOAD_FOLDER']}")
    print(f"💾 Cache file: {UNIFIED_CACHE_FILE}")
    print(f"📊 Download status: {DOWNLOAD_STATUS_FILE}")
    print(f"🕐 Cache duration: 2 hours")
    print(f"🌐 Browser mode: Headless (always)")
    if os.getenv('DYNO'):
        print(f"☁️  Running on Heroku (ephemeral /tmp storage)")
        print(f"🧹 Auto-cleanup enabled when /tmp > 80% full")
    print("="*70)

    load_persistent_data()
    cleanup_old_downloads()

    if os.getenv('DYNO'):
        cleanup_tmp_directory()

    port = int(os.getenv('PORT', 5000))

    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', debug=debug, port=port, threaded=True)
