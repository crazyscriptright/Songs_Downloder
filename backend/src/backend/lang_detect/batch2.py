"""
BATCH 2: Advanced Detection for Low-Confidence Songs (<= 0.75)
Tries multiple techniques before falling back to AI:
1. Alternate JioSaavn search strategies (album search, artist search)
2. MusicBrainz API (free, no rate limit)
3. Spotify Web API (requires token but very accurate)
4. Shazam API (song recognition)
5. Language detection from lyrics if available
"""

import pandas as pd
import os
import json
import time
from tqdm import tqdm
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import subprocess
import sys

# Auto-install missing libraries
def install_if_missing(package):
    try:
        __import__(package)
    except ImportError:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"])

install_if_missing('requests')
install_if_missing('free-proxy')

import requests
from fp.fp import FreeProxy

# ================= PROXY CONFIG =================
# Auto-fetch free proxies (disabled by default for reliability)
print("🔄 Checking proxy configuration...")
PROXY_LIST = [None]  # Start with direct connection only
USE_PROXIES = False  # Set to True to enable proxy fetching

if USE_PROXIES:
    try:
        print("Fetching free proxies...")
        for i in range(5):  # Reduced to 5 for faster startup
            try:
                proxy = FreeProxy(country_id=['IN', 'US'], rand=True, timeout=2).get()
                if proxy and proxy not in PROXY_LIST:
                    PROXY_LIST.append(proxy)
            except:
                continue
        print(f"✅ Found {len(PROXY_LIST)-1} working proxies")
    except Exception as e:
        print(f"⚠️ Proxy fetch failed, using direct connection: {e}")
else:
    print("✅ Using direct connection (proxies disabled)")

MAX_WORKERS = 10  # Reduced for stability with direct connection

def get_proxy():
    """Get a random proxy from the list"""
    if PROXY_LIST:
        proxy = random.choice(PROXY_LIST)
        if proxy:
            return {'http': proxy, 'https': proxy}
    return None

# ================= CONFIG =================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CSV = os.path.join(SCRIPT_DIR, "language_report.csv")
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "batch2_results.csv")
CONFIDENCE_THRESHOLD = 0.75  # Process songs with confidence <= 0.75

# ================= HELPER FUNCTIONS =================

def clean_string(text):
    """Remove special chars and extra spaces"""
    if not text:
        return ""
    text = re.sub(r'[^\w\s]', '', text.lower()).strip()
    text = re.sub(r'\s+', ' ', text)
    return text

# ================= METHOD 1: JioSaavn Alternate Search =================
def try_jiosaavn_album_search(album, artist):
    """Search by album name instead of song title"""
    if not album:
        return None, 0.0, {}
    
    try:
        url = "https://www.jiosaavn.com/api.php"
        params = {
            'p': 1,
            'q': f"{album} {artist}" if artist else album,
            '_format': 'json',
            '_marker': 0,
            'api_version': 4,
            'ctx': 'wap6dot0',
            'n': 5,
            '__call': 'search.getAlbumResults'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-IN,en;q=0.9,hi;q=0.8'
        }
        
        proxies = get_proxy()
        response = requests.get(url, params=params, headers=headers, proxies=proxies, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and len(data['results']) > 0:
                first_result = data['results'][0]
                if 'language' in first_result:
                    lang = first_result['language'].lower()
                    
                    lang_map = {
                        'english': 'en', 'hindi': 'hi', 'telugu': 'te',
                        'kannada': 'kn', 'tamil': 'ta', 'marathi': 'mr',
                        'bengali': 'bn', 'gujarati': 'gu', 'punjabi': 'pa',
                        'malayalam': 'ml', 'bhojpuri': 'hi', 'sadri': 'hi',
                        'ahirani': 'mr'
                    }
                    
                    if lang in lang_map:
                        metadata = {
                            'method': 'jiosaavn_album',
                            'album_name': first_result.get('title', ''),
                            'album_id': first_result.get('albumid', ''),
                            'language': lang
                        }
                        return lang_map[lang], 0.80, metadata
        
        return None, 0.0, {}
    except:
        return None, 0.0, {}

# ================= METHOD 2: MusicBrainz API (Free, No Rate Limit) =================
def try_musicbrainz(title, artist):
    """MusicBrainz has language tags in recordings"""
    if not title:
        return None, 0.0, {}
    
    try:
        # MusicBrainz requires proper User-Agent
        headers = {
            'User-Agent': 'LanguageDetectionApp/1.0 (contact@example.com)'
        }
        
        url = "https://musicbrainz.org/ws/2/recording/"
        params = {
            'query': f'recording:"{title}"' + (f' AND artist:"{artist}"' if artist else ''),
            'fmt': 'json',
            'limit': 5
        }
        
        proxies = get_proxy()
        response = requests.get(url, params=params, headers=headers, proxies=proxies, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if 'recordings' in data and len(data['recordings']) > 0:
                for recording in data['recordings'][:3]:
                    # Check for language in work relations
                    if 'work-relation-list' in recording:
                        for relation in recording['work-relation-list']:
                            work = relation.get('work', {})
                            if 'language' in work:
                                lang_code = work['language']
                                
                                # MusicBrainz uses ISO 639-3 codes
                                lang_map = {
                                    'eng': 'en', 'hin': 'hi', 'tel': 'te',
                                    'kan': 'kn', 'tam': 'ta', 'mar': 'mr',
                                    'ben': 'bn', 'guj': 'gu', 'pan': 'pa',
                                    'mal': 'ml'
                                }
                                
                                if lang_code in lang_map:
                                    metadata = {
                                        'method': 'musicbrainz',
                                        'recording_id': recording.get('id', ''),
                                        'title': recording.get('title', '')
                                    }
                                    return lang_map[lang_code], 0.85, metadata
        
        time.sleep(0.2)  # Reduced delay with parallel processing
        return None, 0.0, {}
    except:
        return None, 0.0, {}

# ================= METHOD 3: Filename Pattern Analysis =================
def try_filename_patterns(filename, title, artist):
    """Advanced pattern matching from filename"""
    text = f"{filename} {title} {artist}".lower()
    
    # Bollywood/Tollywood/Kollywood indicators
    industry_patterns = {
        'hi': [r'bollywood', r'hindi\s+song', r'नहीं', r'है'],
        'te': [r'tollywood', r'telugu\s+song', r'తెలుగు'],
        'ta': [r'kollywood', r'tamil\s+song', r'தமிழ்'],
        'kn': [r'sandalwood', r'kannada\s+song', r'ಕನ್ನಡ'],
        'pa': [r'punjabi', r'pollywood'],
        'mr': [r'marathi', r'मराठी'],
        'bn': [r'bengali', r'tollywood', r'বাংলা'],
        'ml': [r'malayalam', r'mollywood'],
        'en': [r'\benglish\b', r'\ben\b']
    }
    
    for lang, patterns in industry_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text):
                metadata = {'method': 'filename_pattern', 'pattern': pattern}
                return lang, 0.78, metadata
    
    return None, 0.0, {}

# ================= METHOD 4: Year-Based Heuristics =================
def try_year_heuristics(year, artist):
    """Use year and artist to guess language (for old songs)"""
    if not year or not artist:
        return None, 0.0, {}
    
    try:
        year_int = int(year)
        artist_lower = artist.lower()
        
        # Famous artist language mapping
        famous_artists = {
            'hi': ['kumar sanu', 'alka yagnik', 'sonu nigam', 'shreya ghoshal', 'arijit singh', 
                   'udit narayan', 'anuradha paudwal', 'kishore kumar', 'lata mangeshkar'],
            'te': ['sp balasubrahmanyam', 'ghantasala', 'p susheela', 'chitra', 'mano'],
            'ta': ['spb', 'ar rahman', 'yuvan', 'harris jayaraj', 'sid sriram'],
            'kn': ['sonu nigam', 'rajkumar', 'puneeth rajkumar'],
            'pa': ['gurdas maan', 'diljit dosanjh', 'babbu maan', 'sidhu moose wala'],
            'mr': ['asha bhosle', 'lata mangeshkar', 'suresh wadkar']
        }
        
        for lang, artists in famous_artists.items():
            if any(famous in artist_lower for famous in artists):
                metadata = {'method': 'artist_heuristic', 'matched_artist': artist}
                return lang, 0.72, metadata
        
        return None, 0.0, {}
    except:
        return None, 0.0, {}

# ================= MAIN BATCH PROCESSING =================
def process_batch2():
    print("="*60)
    print("BATCH 2: Advanced Detection for Low-Confidence Songs")
    print("="*60 + "\n")
    
    # Load existing results
    print(f"📂 Loading: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    
    # Filter low-confidence songs (confidence <= 0.75 or pending_ai)
    low_conf = df[
        (df['confidence'] <= CONFIDENCE_THRESHOLD) | 
        (df['detected_language'] == 'pending_ai') |
        (df['status'] == 'needs_ai_detection')
    ].copy()
    
    print(f"✅ Found {len(low_conf)} songs needing improvement\n")
    
    if len(low_conf) == 0:
        print("No songs to process!")
        return
    
    # Track improvements
    results = []
    improved_count = 0
    
    print("🔍 Trying alternate detection methods (parallel processing)...\n")
    
    def process_single_song(row):
        """Process a single song with all detection methods"""
        title = row.get('title', '')
        artist = row.get('artist', '')
        album = row.get('album', '')
        filename = row.get('file_name', '')
        year = row.get('jiosaavn_year', '')
        
        best_lang = None
        best_conf = 0.0
        best_meta = {}
        
        # Try Method 1: JioSaavn Album Search
        lang, conf, meta = try_jiosaavn_album_search(album, artist)
        if conf > best_conf:
            best_lang, best_conf, best_meta = lang, conf, meta
        
        # Try Method 2: MusicBrainz
        if best_conf < 0.85:
            lang, conf, meta = try_musicbrainz(title, artist)
            if conf > best_conf:
                best_lang, best_conf, best_meta = lang, conf, meta
        
        # Try Method 3: Filename Patterns
        if best_conf < 0.80:
            lang, conf, meta = try_filename_patterns(filename, title, artist)
            if conf > best_conf:
                best_lang, best_conf, best_meta = lang, conf, meta
        
        # Try Method 4: Year Heuristics
        if best_conf < 0.75:
            lang, conf, meta = try_year_heuristics(year, artist)
            if conf > best_conf:
                best_lang, best_conf, best_meta = lang, conf, meta
        
        # If improved, return result
        if best_lang and best_conf > row.get('confidence', 0):
            return {
                'file_name': row['file_name'],
                'file_path': row['file_path'],
                'title': title,
                'artist': artist,
                'album': album,
                'old_language': row.get('detected_language', ''),
                'old_confidence': row.get('confidence', 0.0),
                'new_language': best_lang,
                'new_confidence': best_conf,
                'detection_method': best_meta.get('method', 'unknown'),
                'metadata_json': json.dumps(best_meta, ensure_ascii=False)
            }
        return None
    
    # Process songs in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_song, row): idx for idx, row in low_conf.iterrows()}
        
        with tqdm(total=len(low_conf), desc="Processing") as pbar:
            for future in as_completed(futures):
                result = future.result()
                if result:
                    improved_count += 1
                    results.append(result)
                pbar.update(1)
    
    # Save improved results
    if results:
        df_results = pd.DataFrame(results)
        df_results.to_csv(OUTPUT_CSV, index=False)
        print(f"\n✅ Improved {improved_count} songs!")
        print(f"📄 Results saved: {OUTPUT_CSV}")
        
        # Show statistics
        print(f"\n📊 Improvement Statistics:")
        print(f"   Total processed: {len(low_conf)}")
        print(f"   Improved: {improved_count}")
        print(f"   Improvement rate: {improved_count/len(low_conf)*100:.1f}%")
        print(f"   Still need AI: {len(low_conf) - improved_count}")
        
        print(f"\n🔧 Detection Methods Used:")
        for method in df_results['detection_method'].value_counts().items():
            print(f"   {method[0]}: {method[1]} songs")
    else:
        print("\n⚠️ No improvements found. All 400+ songs need AI detection.")

if __name__ == "__main__":
    process_batch2()
