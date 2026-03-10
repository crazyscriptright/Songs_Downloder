"""
Test script for SpotiFLAC HTTP endpoint integration

This script tests the /download endpoint with multiple platforms.
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:5000"

# Test URLs for each supported platform
TEST_CASES = [
    {
        "label": "Spotify",
        "url": "https://open.spotify.com/track/5PUXKVVVQ74C3gl5vKy9Li",
        "title": "Heeriye (feat. Arijit Singh)",
        "note": "DRM protected — SpotiFLAC only (no yt-dlp fallback)",
    },
    {
        "label": "YouTube",
        "url": "https://www.youtube.com/watch?v=JGwWNGJdvx8",
        "title": "Shape of You - Ed Sheeran",
        "note": "SpotiFLAC first → yt-dlp fallback",
    },
    {
        "label": "YouTube Music",
        "url": "https://music.youtube.com/watch?v=JGwWNGJdvx8",
        "title": "Shape of You - Ed Sheeran",
        "note": "SpotiFLAC first → yt-dlp fallback",
    },
    {
        "label": "SoundCloud",
        "url": "https://soundcloud.com/octobersveryown/gods-plan",
        "title": "God's Plan - Drake",
        "note": "SpotiFLAC first → yt-dlp fallback",
    },
    {
        "label": "JioSaavn",
        "url": "https://www.jiosaavn.com/song/heeriye/GwNXeyZzc2k",
        "title": "Heeriye",
        "note": "SpotiFLAC first → yt-dlp fallback",
    },
]

def test_download(label: str, url: str, title: str, note: str, wait_for_complete=True):
    """Send a download request and optionally monitor to completion."""

    print(f"\n{'='*70}")
    print(f"Platform : {label}")
    print(f"Note     : {note}")
    print(f"URL      : {url}")
    print(f"{'='*70}")

    payload = {
        "url": url,
        "title": title,
        "advancedOptions": {
            "keepVideo": False,
            "embedSubtitles": False,
            "addMetadata": True,
            "customArgs": "",
            "audioFormat": "flac",
            "audioQuality": "0",
            "embedThumbnail": True,
        },
    }

    try:
        resp = requests.post(f"{BASE_URL}/download", json=payload, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        download_id = result.get("download_id")

        print(f"✅ Queued  →  download_id: {download_id}")

        if not wait_for_complete:
            time.sleep(3)
            status_resp = requests.get(f"{BASE_URL}/download_status/{download_id}", timeout=10)
            status = status_resp.json()
            print(f"   Status : {status.get('status')} | {status.get('eta', '')}")
            return

        print("   Monitoring progress…")
        for _ in range(90):          # up to 3 minutes
            time.sleep(2)
            status_resp = requests.get(f"{BASE_URL}/download_status/{download_id}", timeout=10)
            status = status_resp.json()

            print(
                f"\r   {status.get('progress', 0):>3}% | "
                f"{status.get('status'):<12} | "
                f"{status.get('eta', 'N/A'):<40} | "
                f"{status.get('speed', 'N/A')}",
                end="",
            )

            if status.get("status") == "complete":
                print(f"\n✅ Done  →  {status.get('file')}")
                break
            elif status.get("status") == "error":
                print(f"\n❌ Error →  {status.get('error')}")
                break
        else:
            print("\n⚠️  Timeout — still in progress")

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to http://localhost:5000 — is the backend running?")
    except Exception as exc:
        print(f"❌ {exc}")


def test_download_endpoint():
    """Original single-track test (Spotify FLAC) kept for backwards compatibility."""
    test_download(**TEST_CASES[0], wait_for_complete=True)


def test_mp3_fallback():
    """Show that Spotify + MP3 still routes through SpotiFLAC."""
    test_download(
        label="Spotify (MP3 requested)",
        url=TEST_CASES[0]["url"],
        title=TEST_CASES[0]["title"],
        note="audioFormat=mp3 still uses SpotiFLAC for Spotify (DRM)",
        wait_for_complete=False,
    )


if __name__ == "__main__":
    print("\n>>> SpotiFLAC HTTP Endpoint Test Suite <<<")
    print("Routing: Spotify/JioSaavn/YouTube/YTMusic/SoundCloud → SpotiFLAC → yt-dlp fallback\n")

    # Quick smoke-test all platforms (don't wait for completion)
    print("─── Quick Platform Smoke-Test (no waiting) ───")
    for case in TEST_CASES:
        test_download(**case, wait_for_complete=False)
        time.sleep(1)

    # Full end-to-end test for Spotify
    print("\n─── Full End-to-End Test: Spotify ───")
    test_download(**TEST_CASES[0], wait_for_complete=True)

    print("\n" + "=" * 70)
    print("Routing summary:")
    print("  spotify.com / spotify:   → SpotiFLAC  (no yt-dlp fallback — DRM)")
    print("  jiosaavn.com / saavn.com → SpotiFLAC  → yt-dlp fallback")
    print("  youtube.com / youtu.be   → SpotiFLAC  → yt-dlp fallback")
    print("  music.youtube.com        → SpotiFLAC  → yt-dlp fallback")
    print("  soundcloud.com           → SpotiFLAC  → yt-dlp fallback")
    print("  everything else          → yt-dlp directly")
    print("=" * 70)
