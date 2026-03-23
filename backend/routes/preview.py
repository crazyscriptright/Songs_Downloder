"""
Preview Blueprint
Routes: /preview, /preview_url, /jiosaavn_suggestions/<pid>,
        /extract_jiosaavn_pid, /extract_playlist
"""

import json
import os
import re
import subprocess
import time

import requests
from bs4 import BeautifulSoup
import mimetypes

from flask import Blueprint, Response, jsonify, request, send_file

from core import config
from core import state
from services.preview import (
    download_preview_audio,
    get_jiosaavn_stream_fast,
    get_soundcloud_stream_fast,
)

preview_bp = Blueprint("preview", __name__)

def extract_soundcloud_metadata_with_recommendations(soundcloud_url):
    """Scrape SoundCloud page for track metadata + recommendations."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        url = soundcloud_url.replace("https://soundcloud.com/", "https://m.soundcloud.com/")
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        tracks_scripts = sorted(
            [(i, s) for i, s in enumerate(soup.find_all("script")) if s.string and '"tracks":' in s.string],
            key=lambda x: len(x[1].string), reverse=True,
        )

        script_tag = tracks_scripts[0][1] if tracks_scripts else None
        if not script_tag:
            for s in soup.find_all("script"):
                if s.string and len(s.string) > 50000:
                    if any(k in s.string.lower() for k in ("soundcloud", "track", "audio")):
                        script_tag = s
                        break

        if not script_tag:
            return None

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
            def _find(obj):
                if isinstance(obj, dict):
                    if "tracks" in obj and isinstance(obj["tracks"], dict):
                        t = obj["tracks"]
                        if any(k.startswith("soundcloud:tracks") for k in t):
                            return t
                    for v in obj.values():
                        r = _find(v)
                        if r:
                            return r
                elif isinstance(obj, list):
                    for item in obj:
                        r = _find(item)
                        if r:
                            return r
                return None
            tracks_data = _find(data)

        if not tracks_data:
            return None

        soundcloud_tracks = []
        for key, value in tracks_data.items():
            if not key.startswith("soundcloud:tracks"):
                continue
            td = value.get("data", {})
            duration_ms = td.get("duration", 0)
            duration_str = f"{duration_ms // 60000}:{(duration_ms % 60000) // 1000:02d}" if duration_ms else "0:00"

            artist_name = "Unknown Artist"
            if isinstance(td.get("user"), dict):
                artist_name = td["user"].get("username", "Unknown Artist")
            elif td.get("uploader"):
                artist_name = td["uploader"]
            elif td.get("artist"):
                artist_name = td["artist"]
            else:
                uid = td.get("user_id")
                if uid and users_data:
                    ukey = f"soundcloud:users:{uid}"
                    if ukey in users_data:
                        ui = users_data[ukey].get("data", {})
                        artist_name = ui.get("username", ui.get("display_name", "Unknown Artist"))
                    else:
                        for k, ud in users_data.items():
                            if k.startswith("soundcloud:users:"):
                                ui = ud.get("data", {})
                                if ui.get("id") == uid:
                                    artist_name = ui.get("username", ui.get("display_name", "Unknown Artist"))
                                    break

            soundcloud_tracks.append({
                "id": key,
                "title": td.get("title", "Unknown"),
                "artist": artist_name,
                "url": td.get("permalink_url", soundcloud_url),
                "thumbnail": td.get("artwork_url", ""),
                "duration": duration_str,
                "plays": td.get("playback_count", 0),
                "likes": td.get("likes_count", 0),
                "genre": td.get("genre", ""),
                "created_at": td.get("created_at", ""),
                "source": "SoundCloud",
            })

        if soundcloud_tracks:
            return {
                "main_track": soundcloud_tracks[0],
                "recommended_tracks": soundcloud_tracks[1:] if len(soundcloud_tracks) > 1 else [],
                "total_tracks": len(soundcloud_tracks),
            }
        return None

    except Exception as e:
        print(f"SoundCloud metadata error: {e}")
        return None

def extract_jiosaavn_metadata(jiosaavn_url):
    """Scrape JioSaavn page for track metadata."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(jiosaavn_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        metadata = {}

        for script in soup.find_all("script"):
            if not (script.string and "window.__INITIAL_DATA__" in script.string and '"song":{' in script.string):
                continue
            sc = script.string

            title_m = re.search(
                r'"song":\{"status":"fulfilled","song":\{"type":"song","album":\{"text":"[^"]*","action":"[^"]*"\},"artists":\[.*?\],"breadCrumbs":\[.*?\],"copyright":\{.*?\},"duration":\d+,"encrypted_media_url":"[^"]*","has_lyrics":[^,]*,"id":"([^"]+)".*?"language":"([^"]+)".*?"title":\{"text":"([^"]+)"',
                sc, re.DOTALL,
            )
            if title_m:
                metadata["pid"] = title_m.group(1)
                metadata["language"] = title_m.group(2)
                metadata["title"] = title_m.group(3)

            alb_m = re.search(r'"song":\{"status":"fulfilled","song":\{"type":"song","album":\{"text":"([^"]+)"', sc)
            if alb_m:
                metadata["album"] = alb_m.group(1)

            img_m = re.search(r'"image":\["([^"]+)"\]', sc)
            if img_m:
                metadata["thumbnail"] = img_m.group(1).replace(r"\u002F", "/")

            art_m = re.search(
                r'"song":\{"status":"fulfilled","song":\{"type":"song","album":\{[^}]+\},"artists":\[([^\]]+)\]', sc
            )
            if art_m:
                entries = re.findall(r'\{"id":"[^"]+","name":"([^"]+)","role":"([^"]+)"', art_m.group(1))
                metadata["artists"] = [n for n, r in entries if r in ("singer", "music")]

            if metadata.get("title") and metadata.get("pid"):
                return metadata
            break

        img_el = soup.find("img", {"id": "songHeaderImage"})
        if img_el:
            metadata["thumbnail"] = img_el.get("src")

        h1 = soup.find("h1", class_="u-h2 u-margin-bottom-tiny@sm")
        if h1:
            t = h1.get_text(strip=True)
            metadata["title"] = t[:-6].strip() if t.endswith("Lyrics") else t

        para = soup.find("p", class_="u-color-js-gray u-ellipsis@lg u-margin-bottom-tiny@sm")
        if para:
            alb_link = para.find("a", href=lambda x: x and "/album/" in x)
            if alb_link:
                metadata["album"] = alb_link.get_text(strip=True)
            artists = [a.get_text(strip=True) for a in para.find_all("a", href=lambda x: x and "/artist/" in x)]
            if artists:
                metadata["artists"] = artists

        for script in soup.find_all("script"):
            if script.string and '"pid"' in script.string:
                m = re.search(r'"pid"\s*:\s*"([^"]+)"', script.string)
                if m:
                    metadata["pid"] = m.group(1)
                    break

        for script in soup.find_all("script"):
            if script.string and '"language"' in script.string:
                m = re.search(r'"language"\s*:\s*"([^"]+)"', script.string)
                if m:
                    metadata["language"] = m.group(1)
                    break

        if "language" not in metadata:
            for lang in ("english", "hindi", "tamil", "telugu", "punjabi"):
                if lang in jiosaavn_url.lower() or lang in resp.text.lower():
                    metadata["language"] = lang
                    break
            else:
                metadata["language"] = "hindi"

        return metadata

    except Exception as e:
        print(f"JioSaavn metadata error: {e}")
        return None

def _extract_video_id(url):
    for pat in (r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", r"(?:embed\/)([0-9A-Za-z_-]{11})", r"(?:watch\?v=)([0-9A-Za-z_-]{11})"):
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None

@preview_bp.route("/preview_url", methods=["POST"])
def preview_url():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing URL"}), 400
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return jsonify({"error": "Invalid URL format"}), 400

    try:
        source = "Unknown"
        if "soundcloud.com" in url.lower():
            source = "SoundCloud"
        elif "jiosaavn.com" in url.lower() or "saavn.com" in url.lower():
            source = "JioSaavn"
        elif "open.spotify.com" in url.lower():
            source = "Spotify"
        elif any(p in url.lower() for p in ("youtube.com", "youtu.be", "music.youtube.com")):
            source = "YouTube"

        if source == "YouTube":
            vid = _extract_video_id(url)
            if not vid:
                return jsonify({"error": "Invalid YouTube URL"}), 400
            from routes.search import get_apis
            try:
                _, ytvideo, _ = get_apis()
                data_yt = ytvideo.search_videos(vid, use_fresh_tokens=True, retry_on_error=False)
                if data_yt:
                    videos = ytvideo.parse_video_results(data_yt)
                    if videos:
                        v = videos[0]
                        return jsonify({
                            "title": v.get("title", "Unknown Title"),
                            "uploader": v.get("metadata", "Unknown Channel"),
                            "channel": v.get("metadata", "Unknown Channel"),
                            "thumbnail": v.get("thumbnail", f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg"),
                            "video_id": vid,
                            "webpage_url": f"https://www.youtube.com/watch?v={vid}",
                            "source": "YouTube",
                        })
            except Exception:
                pass
            return jsonify({
                "title": "YouTube Video", "uploader": "Unknown Channel", "channel": "Unknown Channel",
                "thumbnail": f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg",
                "video_id": vid, "webpage_url": url, "source": "YouTube",
            })

        if source == "JioSaavn":
            meta = extract_jiosaavn_metadata(url)
            if not meta:
                return jsonify({"error": "Invalid JioSaavn URL"}), 400
            artists_arr = meta.get("artists", [])
            artist_str = ", ".join(artists_arr) if artists_arr else "Unknown Artist"
            return jsonify({
                "title": meta.get("title", "JioSaavn Content"),
                "uploader": artist_str, "channel": artist_str,
                "artists": artists_arr,
                "thumbnail": meta.get("thumbnail", ""),
                "album": meta.get("album", ""),
                "pid": meta.get("pid", ""),
                "language": meta.get("language", "hindi"),
                "webpage_url": url, "source": source,
            })

        if source == "SoundCloud":
            meta = extract_soundcloud_metadata_with_recommendations(url)
            if not meta or not meta.get("main_track"):
                return jsonify({"error": "Invalid SoundCloud URL"}), 400
            mt = meta["main_track"]
            return jsonify({
                "title": mt.get("title", "SoundCloud Content"),
                "uploader": mt.get("artist", source), "channel": mt.get("artist", source),
                "thumbnail": mt.get("thumbnail", ""),
                "duration": mt.get("duration", ""), "plays": mt.get("plays", 0),
                "likes": mt.get("likes", 0), "genre": mt.get("genre", ""),
                "webpage_url": url, "source": source,
                "soundcloud_data": meta,
            })

        if source == "Spotify":
            import re as _re
            m = _re.search(r"open\.spotify\.com/track/([A-Za-z0-9]+)", url)
            if not m:
                return jsonify({"error": "Invalid Spotify track URL"}), 400
            track_id = m.group(1)
            from routes.search import get_spotify_client
            spotify_client = get_spotify_client()
            track = spotify_client.get_track_metadata(track_id)
            # format duration_ms → "m:ss"
            dur_ms = track.get("duration_ms", 0)
            total_sec = (dur_ms or 0) // 1000
            duration_str = f"{total_sec // 60}:{total_sec % 60:02d}"
            return jsonify({
                "title":       track.get("title", "Unknown Title"),
                "uploader":    track.get("artist", "Unknown Artist"),
                "channel":     track.get("album_artist", track.get("artist", "")),
                "album":       track.get("album", ""),
                "thumbnail":   track.get("cover_url", ""),
                "duration":    duration_str,
                "year":        (track.get("release_date") or "")[:4] or None,
                "isrc":        track.get("isrc", ""),
                "webpage_url": url,
                "source":      "Spotify",
            })

        return jsonify({"error": f"Invalid {source} URL — unable to extract information"}), 400

    except Exception as e:
        print(f"❌ Preview URL error: {e}")
        return jsonify({"error": str(e)}), 500

@preview_bp.route("/preview", methods=["GET"])
def audio_preview():
    """
    Resolve and serve a low-quality audio preview.

    Resolution order:
      1. SoundCloud / JioSaavn native API → CDN URL → proxied
      2. yt-dlp actual download → temp file → served with send_file
    """
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing url parameter"}), 400
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return jsonify({"error": "Invalid URL"}), 400

    cached_val = None
    cached = state.preview_cache.get(url)
    if cached:
        _val, expires_at = cached
        if time.time() < expires_at:

            if _val.startswith("http") or (os.path.isfile(_val) and os.path.getsize(_val) > 0):
                cached_val = _val
        if not cached_val:
            state.preview_cache.pop(url, None)

    def _cache_store(value: str) -> None:
        if len(state.preview_cache) >= config.PREVIEW_CACHE_MAX_SIZE:
            oldest = next(iter(state.preview_cache))
            state.preview_cache.pop(oldest, None)
        state.preview_cache[url] = (value, time.time() + config.PREVIEW_CACHE_TTL)

    cdn_url: str | None = None
    file_path: str | None = None

    if cached_val:
        if cached_val.startswith("http"):
            cdn_url = cached_val
        else:
            file_path = cached_val
    else:
        url_lower = url.lower()

        file_path = download_preview_audio(url)

        if not file_path:
            if "soundcloud.com" in url_lower:
                try:
                    from integrations import soundcloud
                    client_id = soundcloud.get_valid_client_id()
                    cdn_url = get_soundcloud_stream_fast(url, client_id)
                except Exception as e:
                    print(f"[/preview] SoundCloud fallback error: {e}")
            elif "jiosaavn.com" in url_lower or "saavn.com" in url_lower:
                cdn_url = get_jiosaavn_stream_fast(url)

        if file_path:
            _cache_store(file_path)
        elif cdn_url:
            _cache_store(cdn_url)

    if not cdn_url and not file_path:
        return jsonify({"error": "Preview unavailable"}), 503

    if file_path:
        try:
            mime, _ = mimetypes.guess_type(file_path)
            return send_file(
                file_path,
                mimetype=mime or "audio/mpeg",
                conditional=True,
                max_age=config.PREVIEW_CACHE_TTL,
            )
        except Exception as e:
            print(f"[/preview] send_file failed: {e}")
            return jsonify({"error": "Preview unavailable"}), 503

    try:
        proxy_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        rng = request.headers.get("Range")
        if rng:
            proxy_headers["Range"] = rng

        upstream = requests.get(cdn_url, headers=proxy_headers, stream=True, timeout=10)
        if not upstream.ok:

            state.preview_cache.pop(url, None)
            file_path = download_preview_audio(url)
            if file_path:
                _cache_store(file_path)
                mime, _ = mimetypes.guess_type(file_path)
                return send_file(
                    file_path,
                    mimetype=mime or "audio/mpeg",
                    conditional=True,
                    max_age=config.PREVIEW_CACHE_TTL,
                )
            return jsonify({"error": "Preview unavailable"}), 503

        content_type = upstream.headers.get("Content-Type", "audio/mpeg")
        resp_headers = {
            "Content-Type": content_type,
            "Accept-Ranges": "bytes",
            "Cache-Control": f"public, max-age={config.PREVIEW_CACHE_TTL}",
            "X-Content-Type-Options": "nosniff",
        }
        if "Content-Length" in upstream.headers:
            resp_headers["Content-Length"] = upstream.headers["Content-Length"]
        if "Content-Range" in upstream.headers:
            resp_headers["Content-Range"] = upstream.headers["Content-Range"]

        return Response(upstream.iter_content(chunk_size=4096), status=upstream.status_code, headers=resp_headers)
    except Exception as e:
        print(f"[/preview] CDN proxy failed: {e}")
        return jsonify({"error": "Stream proxy failed"}), 502

@preview_bp.route("/jiosaavn_suggestions/<pid>")
def get_jiosaavn_suggestions_by_pid(pid):
    if not pid or not re.match(r"^[a-zA-Z0-9_-]{1,20}$", pid):
        return jsonify({"error": "Invalid PID format"}), 400

    language = request.args.get("language", "english")
    ALLOWED_LANGS = ("english", "hindi", "telugu", "tamil", "punjabi", "bengali", "marathi", "gujarati", "kannada", "malayalam")
    if language not in ALLOWED_LANGS:
        language = "english"

    suggestions = []
    method_used = "api"

    try:
        from integrations.jiosaavn_suggestions_simple import JioSaavnSuggestions
        scraper = JioSaavnSuggestions()
        suggestions = scraper.get_suggestions(pid, language, max_results=10)
        if suggestions:
            method_used = "artistOtherTopSongs"
    except Exception as e:
        print(f"JioSaavn suggestions error: {e}")

    if suggestions:
        return jsonify({"success": True, "pid": pid, "language": language, "suggestions": suggestions, "count": len(suggestions), "method": method_used})
    return jsonify({"success": False, "error": "No suggestions available", "pid": pid, "language": language, "suggestions": [], "count": 0, "method": method_used}), 404

@preview_bp.route("/extract_jiosaavn_pid", methods=["POST"])
def extract_jiosaavn_pid():
    try:
        data = request.get_json()
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"error": "URL is required"}), 400
        if "jiosaavn.com" not in url and "saavn.com" not in url:
            return jsonify({"error": "Not a valid JioSaavn URL"}), 400
        meta = extract_jiosaavn_metadata(url)
        if meta and "pid" in meta:
            return jsonify({"success": True, "pid": meta["pid"], "metadata": meta})
        return jsonify({"error": "Could not extract PID"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@preview_bp.route("/extract_playlist", methods=["POST"])
def extract_playlist():
    data = request.get_json()
    playlist_url = data.get("url")
    playlist_items = data.get("playlistItems", "")
    if not playlist_url:
        return jsonify({"error": "No playlist URL provided"}), 400
    try:
        cmd = ["yt-dlp", "--flat-playlist", "--get-id", "--get-title"]
        if playlist_items:
            cmd.extend(["--playlist-items", playlist_items])
        cmd.append(playlist_url)

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False)
        stdout, stderr = proc.communicate(timeout=30)
        if proc.returncode != 0:
            return jsonify({"error": stderr.strip() or "Failed to extract playlist"}), 400

        lines = [ln.strip() for ln in stdout.strip().split("\n") if ln.strip()]
        videos = [
            {"title": lines[i], "url": f"https://www.youtube.com/watch?v={lines[i+1]}", "video_id": lines[i+1]}
            for i in range(0, len(lines) - 1, 2)
        ]
        return jsonify({"success": True, "videos": videos, "count": len(videos)})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Playlist extraction timed out"}), 408
    except Exception as e:
        return jsonify({"error": str(e)}), 500
