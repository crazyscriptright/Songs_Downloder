"""
Search Blueprint
Routes: /, /search, /search/jiosaavn, /search/soundcloud,
        /search/ytmusic, /search/ytvideo, /suggestions, /search_status/<id>
"""

import os
import re
import threading
import urllib.parse
from datetime import datetime

import requests
from flask import Blueprint, jsonify, render_template, request

import state
from utils.url_utils import is_url, validate_url_simple

search_bp = Blueprint("search", __name__)

# ── Lazy API singletons ───────────────────────────────────────────────────────

_ytmusic_api = None
_ytvideo_api = None
_jiosaavn_api = None


def get_apis():
    global _ytmusic_api, _ytvideo_api, _jiosaavn_api
    from integrations.ytmusic_dynamic_tokens import YouTubeMusicAPI
    from integrations.ytmusic_dynamic_video_tokens import YouTubeMusicVideoAPI
    from integrations.jiosaavn_search import JioSaavnAPI
    import config

    if not _ytmusic_api:
        _ytmusic_api = YouTubeMusicAPI(
            cache_file=config.UNIFIED_CACHE_FILE,
            cache_duration_hours=config.API_CACHE_HOURS,
            headless=True,
        )
    if not _ytvideo_api:
        _ytvideo_api = YouTubeMusicVideoAPI(
            cache_file=config.UNIFIED_CACHE_FILE,
            cache_duration_hours=config.API_CACHE_HOURS,
            headless=True,
        )
    if not _jiosaavn_api:
        _jiosaavn_api = JioSaavnAPI()
    return _ytmusic_api, _ytvideo_api, _jiosaavn_api


# ── Search helpers ─────────────────────────────────────────────────────────────

def search_ytmusic(query):
    results = []
    try:
        ytmusic, _, _ = get_apis()
        data = ytmusic.search(query, use_fresh_tokens=True, retry_on_error=True)
        songs = ytmusic.parse_search_results(data) if data else []
        for song in songs:
            thumbnail_url = song.get("thumbnail", f"https://img.youtube.com/vi/{song['video_id']}/mqdefault.jpg")
            results.append({
                "title": song["title"],
                "artist": song["metadata"],
                "source": "YouTube Music",
                "url": song["url"],
                "video_id": song["video_id"],
                "thumbnail": thumbnail_url,
                "type": "song",
            })
    except Exception as e:
        print(f"YT Music error: {e}")
    return results


def search_ytvideo(query):
    results = []
    try:
        _, ytvideo, _ = get_apis()
        data = ytvideo.search_videos(query, use_fresh_tokens=True, retry_on_error=True)
        videos = ytvideo.parse_video_results(data) if data else []
        for video in videos:
            thumbnail_url = video.get("thumbnail", f"https://img.youtube.com/vi/{video['video_id']}/mqdefault.jpg")
            results.append({
                "title": video["title"],
                "artist": video["metadata"],
                "source": "YouTube Video",
                "url": video["url"],
                "video_id": video["video_id"],
                "thumbnail": thumbnail_url,
                "type": "video",
            })
    except Exception as e:
        print(f"YT Video error: {e}")
    return results


def search_jiosaavn(query):
    results = []
    try:
        _, _, jiosaavn = get_apis()
        data = jiosaavn.search_songs(query)
        songs = jiosaavn.parse_results(data) if data else []
        for song in songs:
            artist = (
                song.get("primary_artists")
                or song.get("singers")
                or (song.get("subtitle", "").split(" - ")[0] if " - " in song.get("subtitle", "") else "Unknown Artist")
            )
            results.append({
                "title": song["title"],
                "artist": artist,
                "subtitle": song.get("subtitle", ""),
                "source": "JioSaavn",
                "url": song["perma_url"],
                "song_id": song["id"],
                "thumbnail": song.get("image", ""),
                "year": song.get("year", ""),
                "language": song.get("language", ""),
                "play_count": song.get("play_count", ""),
                "type": "song",
            })
    except Exception as e:
        print(f"JioSaavn error: {e}")
    return results


def search_soundcloud(query):
    from integrations import soundcloud
    results = []
    try:
        tracks = soundcloud.soundcloud_search(query, limit=20)
        for track in tracks:
            duration_ms = track.get("duration_ms", 0)
            duration = f"{duration_ms // 60000}:{(duration_ms % 60000) // 1000:02d}" if duration_ms else "0:00"
            artwork_url = track.get("artwork_url", "")
            if artwork_url:
                artwork_url = artwork_url.replace("-large.", "-t500x500.")
            results.append({
                "title": track.get("title", "Unknown"),
                "artist": track.get("uploader", "Unknown Artist"),
                "source": "SoundCloud",
                "url": track.get("url", ""),
                "thumbnail": artwork_url,
                "duration": duration,
                "track_id": track.get("id", ""),
                "plays": track.get("playback_count", 0),
                "likes": track.get("likes_count", 0),
                "genre": track.get("genre", ""),
                "type": "song",
            })
    except Exception as e:
        print(f"SoundCloud error: {e}")
    return results


def search_all_sources(query, search_id, search_type="music"):
    all_results = {
        "ytmusic": [], "ytvideo": [], "jiosaavn": [], "soundcloud": [],
        "direct_url": [], "status": "searching",
        "query_type": "url" if is_url(query) else "search",
    }

    if is_url(query):
        all_results["status"] = "validating"
        state.search_results[search_id] = all_results
        video_info = validate_url_simple(query)
        if video_info and video_info.get("is_valid"):
            all_results["direct_url"] = [video_info]
            all_results["status"] = "complete"
            all_results["message"] = "Valid URL - Ready to download"
        else:
            all_results["status"] = "error"
            all_results["error"] = video_info.get("error", "Invalid URL")
            all_results["message"] = f"Unable to process URL: {video_info.get('error', 'Unknown error')}"
        all_results["timestamp"] = datetime.now().isoformat()
        state.search_results[search_id] = all_results
        return all_results

    threads = []
    lock = threading.Lock()

    def run_search(source_name, fn):
        try:
            res = fn(query)
            with lock:
                all_results[source_name] = res
        except Exception as e:
            print(f"Error searching {source_name}: {e}")

    if search_type == "music":
        threads = [
            threading.Thread(target=run_search, args=("ytmusic", search_ytmusic)),
            threading.Thread(target=run_search, args=("jiosaavn", search_jiosaavn)),
            threading.Thread(target=run_search, args=("soundcloud", search_soundcloud)),
        ]
    elif search_type == "video":
        threads = [threading.Thread(target=run_search, args=("ytvideo", search_ytvideo))]
    else:
        threads = [
            threading.Thread(target=run_search, args=("ytmusic", search_ytmusic)),
            threading.Thread(target=run_search, args=("ytvideo", search_ytvideo)),
            threading.Thread(target=run_search, args=("jiosaavn", search_jiosaavn)),
            threading.Thread(target=run_search, args=("soundcloud", search_soundcloud)),
        ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    all_results["status"] = "complete"
    all_results["timestamp"] = datetime.now().isoformat()
    state.search_results[search_id] = all_results
    return all_results


# ── Suggestion helpers ─────────────────────────────────────────────────────────

def _yt_suggestions(query):
    BLOCK_WORDS = [
        "movie", "full movie", "trailer", "teaser", "film", "scene",
        "dialogue", "review", "tutorial", "how to", "recipe", "meaning",
        "in english", "in hindi", "in telugu", "in tamil", "translation",
        "benefits", "ringtone download", "mp3 ringtone", "ringtone free",
        "download mp3 ringtone",
    ]
    POSTFIX = r"\s+(song|lyrics|audio|music|mp3|cover|bgm|theme|remix|acoustic|live|official|video|album|track|download|ringtone)s?$"
    try:
        enc = urllib.parse.quote(query)
        url = f"https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={enc}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Accept": "application/json",
            "DNT": "1",
        }
        px = {}
        purl = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
        if purl:
            px = {"http": purl, "https": purl}

        resp = requests.get(url, timeout=3, headers=headers, proxies=px or None)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) >= 2:
                raw = data[1] if isinstance(data[1], list) else []
                seen = set()
                out = []
                for s in raw:
                    if not isinstance(s, str):
                        continue
                    norm = s.lower().strip()
                    if not norm:
                        continue
                    cleaned = norm
                    while True:
                        nc = re.sub(POSTFIX, "", cleaned, flags=re.IGNORECASE).strip()
                        if nc == cleaned:
                            break
                        cleaned = nc
                    if not cleaned or cleaned in seen:
                        continue
                    if any(bw in cleaned for bw in BLOCK_WORDS):
                        continue
                    seen.add(cleaned)
                    orig = s
                    while True:
                        nc = re.sub(POSTFIX, "", orig, flags=re.IGNORECASE).strip()
                        if nc == orig:
                            break
                        orig = nc
                    out.append(orig)
                return out[:5]
    except Exception as e:
        print(f"YouTube suggestions error: {e}")
    return []


def _jiosaavn_suggestions(query):
    try:
        from integrations.jiosaavn_search import JioSaavnAPI
        api = JioSaavnAPI()
        results = api.search_songs(query, limit=3)
        if results and "data" in results:
            return [
                s["title"] for s in results["data"]["results"][:3]
                if "title" in s and len(s["title"]) > 3
            ]
    except Exception as e:
        print(f"JioSaavn suggestions error: {e}")
    return []


# ── Routes ────────────────────────────────────────────────────────────────────

@search_bp.route("/")
def index():
    query = request.args.get("q", "").strip()
    search_type = request.args.get("type", "music")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5000")
    return render_template("index.html",
                           initial_query=query,
                           initial_type=search_type,
                           frontend_url=frontend_url)


@search_bp.route("/search", methods=["POST"])
def search():
    data = request.get_json()
    query = data.get("query", "").strip()
    search_type = data.get("type", "music")
    if not query:
        return jsonify({"error": "Empty query"}), 400
    search_id = f"search_{datetime.now().timestamp()}"
    query_type = "url" if is_url(query) else "search"
    threading.Thread(target=search_all_sources, args=(query, search_id, search_type)).start()
    return jsonify({"search_id": search_id, "status": "started", "query_type": query_type})


@search_bp.route("/search/jiosaavn", methods=["POST"])
def search_jiosaavn_endpoint():
    data = request.get_json()
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query is required"}), 400
    try:
        results = search_jiosaavn(query)
        return jsonify({"status": "complete", "source": "jiosaavn", "results": results, "count": len(results), "query": query})
    except Exception as e:
        return jsonify({"status": "error", "source": "jiosaavn", "error": str(e), "results": [], "count": 0, "query": query})


@search_bp.route("/search/soundcloud", methods=["POST"])
def search_soundcloud_endpoint():
    data = request.get_json()
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query is required"}), 400
    try:
        results = search_soundcloud(query)
        return jsonify({"status": "complete", "source": "soundcloud", "results": results, "count": len(results), "query": query})
    except Exception as e:
        return jsonify({"status": "error", "source": "soundcloud", "error": str(e), "results": [], "count": 0, "query": query})


@search_bp.route("/search/ytmusic", methods=["POST"])
def search_ytmusic_endpoint():
    data = request.get_json()
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query is required"}), 400
    try:
        results = search_ytmusic(query)
        return jsonify({"status": "complete", "source": "ytmusic", "results": results, "count": len(results), "query": query})
    except Exception as e:
        return jsonify({"status": "error", "source": "ytmusic", "error": str(e), "results": [], "count": 0, "query": query})


@search_bp.route("/search/ytvideo", methods=["POST"])
def search_ytvideo_endpoint():
    data = request.get_json()
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query is required"}), 400
    try:
        results = search_ytvideo(query)
        return jsonify({"status": "complete", "source": "ytvideo", "results": results, "count": len(results), "query": query})
    except Exception as e:
        return jsonify({"status": "error", "source": "ytvideo", "error": str(e), "results": [], "count": 0, "query": query})


@search_bp.route("/suggestions")
def get_suggestions():
    query = request.args.get("q", "").strip()
    if not query or len(query) < 2:
        return jsonify({"suggestions": []})
    try:
        combined = _yt_suggestions(query)[:4] + _jiosaavn_suggestions(query)[:2]
        seen = set()
        unique = []
        for s in combined:
            k = s.lower().strip()
            if k not in seen and len(k) > 1:
                seen.add(k)
                unique.append(s)
        return jsonify({"suggestions": unique[:6]})
    except Exception as e:
        print(f"Suggestions error: {e}")
        return jsonify({"suggestions": [f"{query} song", f"{query} music", f"{query} latest"]})


@search_bp.route("/search_status/<search_id>")
def search_status(search_id):
    if search_id in state.search_results:
        return jsonify(state.search_results[search_id])
    return jsonify({"status": "not_found"}), 404
