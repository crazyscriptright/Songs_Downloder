import re
import requests
import json
import time
import os
from urllib.parse import quote_plus
from utils.atomic_write import atomic_json_write, atomic_json_read_modify_write
from datetime import datetime, timedelta

# Use unified music_api_cache.json like ytmusic and spotify
CACHE_FILE = "/tmp/music_api_cache.json" if os.getenv("DYNO") else "music_api_cache.json"
CACHE_DURATION_HOURS = 24  # 24 hours cache validity


def load_cache():
    """Load existing soundcloud cache from music_api_cache.json if not expired."""
    try:
        if not os.path.exists(CACHE_FILE):
            return {}
        
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        
        if "soundcloud" not in cache_data:
            return {}
        
        entry = cache_data["soundcloud"]
        cached_time = datetime.fromisoformat(entry["timestamp"])
        expiry_time = cached_time + timedelta(hours=CACHE_DURATION_HOURS)
        
        if datetime.now() < expiry_time:
            return entry  # return the full entry with timestamp
        else:
            return {}  # expired
    except Exception:
        return {}


def save_cache(client_id, app_version="1761662631", user_id=""):
    """Save soundcloud cache to music_api_cache.json (atomic, race-condition-safe)."""
    entry = {
        "client_id": client_id,
        "app_version": app_version,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
    }
    
    try:
        def _updater(cache_data: dict) -> dict:
            cache_data["soundcloud"] = entry
            return cache_data
        
        atomic_json_read_modify_write(CACHE_FILE, _updater, ensure_ascii=False)
        return entry
    except Exception as e:
        print(f"Error saving soundcloud cache: {e}")
        return entry


def get_valid_client_id(force_refresh=False):
    """Return cached or freshly scraped client_id."""
    cache = load_cache()
    if not force_refresh and "client_id" in cache:
        print(f"[Cache] Using cached client_id: {cache['client_id']}")
        return cache["client_id"]

    print("[Fetch] Grabbing new client_id from SoundCloud...")
    page = requests.get("https://soundcloud.com/discover").text
    js_links = re.findall(r'https://a-v2\.sndcdn\.com/assets/[^"]+\.js', page)
    for js_url in js_links[:10]:
        js_code = requests.get(js_url).text
        match = re.search(r'client_id:"([a-zA-Z0-9]+)"', js_code)
        if match:
            client_id = match.group(1)
            save_cache(client_id)
            print(f"[Fetch] New client_id: {client_id}")
            return client_id
    raise RuntimeError("No valid client_id found. SoundCloud may have changed layout.")


def soundcloud_search(query, limit=20, offset=0):
    """Perform a SoundCloud search using cached client_id."""
    app_version = "1761662631"
    user_id = ""
    q = quote_plus(query)

    client_id = get_valid_client_id()

    url = (
        f"https://api-v2.soundcloud.com/search?q={q}&facet=model"
        f"&user_id={user_id}&client_id={client_id}"
        f"&limit={limit}&offset={offset}&linked_partitioning=1"
        f"&app_version={app_version}&app_locale=en"
    )
    print(f"[API] Fetching results for: '{query}'")

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    r = requests.get(url, headers=headers)

    # If 401, refresh client_id automatically
    if r.status_code == 401:
        print("[Warning] client_id expired. Refreshing...")
        client_id = get_valid_client_id(force_refresh=True)
        url = url.replace(client_id, client_id)
        r = requests.get(url, headers=headers)

    if r.status_code != 200:
        raise RuntimeError(f"Request failed ({r.status_code}): {r.text[:200]}")

    data = r.json()
    tracks = [
        {
            "id": t.get("id"),
            "title": t.get("title"),
            "uploader": t.get("user", {}).get("username"),
            "url": t.get("permalink_url"),
            "duration_ms": t.get("duration"),
        }
        for t in data.get("collection", [])
        if "title" in t
    ]

    return tracks


if __name__ == "__main__":
    song=input("type to search SoundCloudtracks...")
    results = soundcloud_search(song)
    print(f"\nFound {len(results)} tracks:")
    for track in results[:5]:
        print(f" {track['title']} — {track['uploader']}")
        print(f" {track['url']}\n")
