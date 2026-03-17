"""
BATCH 3: Advanced API Search Using Song Keywords
Uses different keyword combinations from metadata to search JioSaavn API.
Then compares with Batch 2 results - if both agree, it's marked as FINAL.
This processes songs with confidence <= 0.75.
"""

import pandas as pd
import json
import re
import os
import time
from tqdm import tqdm
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
BATCH2_CSV = os.path.join(SCRIPT_DIR, "batch2_results.csv")
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "batch3_results.csv")
UPDATED_REPORT_CSV = os.path.join(SCRIPT_DIR, "language_report_updated.csv")

# Map language names to codes
LANG_CODE_MAP = {
    'hindi': 'hi', 'telugu': 'te', 'tamil': 'ta', 'kannada': 'kn',
    'punjabi': 'pa', 'marathi': 'mr', 'bengali': 'bn', 'gujarati': 'gu',
    'malayalam': 'ml', 'bhojpuri': 'hi', 'english': 'en',
    'sadri': 'hi', 'ahirani': 'mr', 'urdu': 'ur', 'odia': 'or', 'assamese': 'as'
}

def clean_text(text):
    """Clean and normalize text for matching"""
    if not text or pd.isna(text):
        return ""
    # Convert to string first to handle float/int values
    text = str(text) if not isinstance(text, str) else text
    return re.sub(r'[^\w\s]', ' ', text.lower()).strip()

def search_jiosaavn_with_keywords(title, artist, album):
    """Try multiple keyword combinations to search JioSaavn API"""
    
    # Convert to strings and handle NaN/None values
    title = str(title) if title and not pd.isna(title) else ""
    artist = str(artist) if artist and not pd.isna(artist) else ""
    album = str(album) if album and not pd.isna(album) else ""
    
    if not title:
        return None, 0.0, {}
    
    # Generate different search queries
    search_queries = []
    
    # Query 1: Title only
    search_queries.append(title)
    
    # Query 2: Title + Artist
    if artist:
        search_queries.append(f"{title} {artist}")
    
    # Query 3: Album + Artist (sometimes better for movie soundtracks)
    if album and artist:
        search_queries.append(f"{album} {artist}")
    
    # Query 4: Album only
    if album:
        search_queries.append(album)
    
    # Query 5: Extract keywords from title (remove "feat", "ft", etc)
    clean_title = re.sub(r'\b(feat|ft|featuring|remix|cover|version)\b\.?', '', title, flags=re.IGNORECASE)
    if clean_title != title:
        search_queries.append(clean_title.strip())
    
    best_result = None
    best_score = 0
    best_metadata = {}
    
    for query_idx, query in enumerate(search_queries[:3]):  # Try top 3 queries only
        try:
            url = "https://www.jiosaavn.com/api.php"
            params = {
                'p': 1,
                'q': query.strip(),
                '_format': 'json',
                '_marker': 0,
                'api_version': 4,
                'ctx': 'wap6dot0',
                'n': 5,  # Get 5 results per query
                '__call': 'search.getResults'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-IN,en;q=0.9,hi;q=0.8',
                'Referer': 'https://www.jiosaavn.com/',
                'Origin': 'https://www.jiosaavn.com'
            }
            
            proxies = get_proxy()
            response = requests.get(url, params=params, headers=headers, proxies=proxies, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'results' in data and len(data['results']) > 0:
                    for result in data['results']:
                        if 'language' in result:
                            # Calculate match score
                            score = calculate_match_score(title, artist, album, result)
                            
                            if score > best_score:
                                best_score = score
                                best_result = result
                                best_metadata = {
                                    'query_used': query,
                                    'query_index': query_idx,
                                    'match_score': score,
                                    'jiosaavn_id': result.get('id', ''),
                                    'jiosaavn_title': result.get('title', ''),
                                    'jiosaavn_subtitle': result.get('subtitle', ''),
                                    'jiosaavn_language': result.get('language', ''),
                                    'jiosaavn_year': result.get('year', ''),
                                    'jiosaavn_play_count': result.get('play_count', ''),
                                    'method': 'batch3_api_keyword'
                                }
            
        except Exception as e:
            continue
    
    # Convert result to language code
    if best_result and best_score >= 30:  # Minimum threshold
        lang = best_result['language'].lower()
        lang_code = LANG_CODE_MAP.get(lang, lang)
        
        # Calculate confidence based on score
        if best_score >= 100:
            confidence = 0.90
        elif best_score >= 80:
            confidence = 0.85
        elif best_score >= 60:
            confidence = 0.80
        elif best_score >= 40:
            confidence = 0.75
        else:
            confidence = 0.70
        
        return lang_code, confidence, best_metadata
    
    return None, 0.0, {}

def calculate_match_score(title, artist, album, result):
    """Calculate match score between query and result"""
    score = 0
    
    result_title = clean_text(result.get('title', ''))
    result_subtitle = clean_text(result.get('subtitle', ''))
    result_album = clean_text(result.get('more_info', {}).get('album', ''))
    
    # Convert and clean input values
    clean_title = clean_text(str(title) if title else '')
    clean_artist = clean_text(str(artist) if artist else '')
    clean_album = clean_text(str(album) if album else '')
    
    # Remove leading track numbers
    clean_title = re.sub(r'^\d+[\s\-\.]+', '', clean_title)
    result_title = re.sub(r'^\d+[\s\-\.]+', '', result_title)
    
    # Title matching (most important)
    if clean_title == result_title:
        score += 100
    elif clean_title in result_title or result_title in clean_title:
        score += 70
    elif any(word in result_title for word in clean_title.split() if len(word) > 3):
        score += 40
    
    # Artist matching
    if clean_artist:
        artist_words = [w for w in clean_artist.split() if len(w) > 2]
        if artist_words:
            matches = sum(1 for word in artist_words if word in result_subtitle)
            if matches == len(artist_words):
                score += 50
            elif matches > 0:
                score += 25
    
    # Album matching
    if clean_album and result_album:
        if clean_album == result_album:
            score += 30
        elif clean_album in result_album or result_album in clean_album:
            score += 15
    
    # Song type bonus
    if result.get('type') == 'song':
        score += 10
    
    return score

def process_batch3():
    print("="*60)
    print("BATCH 3: Advanced API Keyword Search")
    print("="*60 + "\n")
    
    # Load main CSV
    print(f"📂 Loading: {INPUT_CSV}")
    df_main = pd.read_csv(INPUT_CSV)
    
    # Load batch2 results if exists
    batch2_results = {}
    if os.path.exists(BATCH2_CSV):
        print(f"📂 Loading: {BATCH2_CSV}")
        df_batch2 = pd.read_csv(BATCH2_CSV)
        # Store as dict: file_path -> (language, confidence)
        for _, row in df_batch2.iterrows():
            batch2_results[row['file_path']] = {
                'language': row['new_language'],
                'confidence': row['new_confidence'],
                'method': row.get('detection_method', 'unknown')
            }
        print(f"✅ Batch 2 results: {len(batch2_results)} songs\n")
    
    # Filter songs with confidence <= 0.75
    low_conf = df_main[
        (df_main['confidence'] <= 0.75) | 
        (df_main['detected_language'] == 'pending_ai') |
        (df_main['status'] == 'needs_ai_detection')
    ].copy()
    
    print(f"✅ Found {len(low_conf)} songs with confidence <= 0.75\n")
    
    if len(low_conf) == 0:
        print("No songs to process!")
        return
    
    batch3_results = []
    final_verified = []
    improved_count = 0
    verified_count = 0
    
    # Store updates to apply to main dataframe
    updates_map = {}  # file_path -> update dict
    
    print("🔍 Searching JioSaavn with keyword combinations (parallel processing)...\n")
    
    def process_single_song(row):
        """Process a single song with API keyword search"""
        title = row.get('title', '')
        artist = row.get('artist', '')
        album = row.get('album', '')
        file_path = row.get('file_path', '')
        
        # Try API search with multiple keyword combinations
        lang, conf, metadata = search_jiosaavn_with_keywords(title, artist, album)
        
        old_conf = row.get('confidence', 0.0)
        old_lang = row.get('detected_language', '')
        
        if lang and conf > old_conf:
            result = {
                'file_name': row['file_name'],
                'file_path': file_path,
                'title': title,
                'artist': artist,
                'album': album,
                'old_language': old_lang,
                'old_confidence': old_conf,
                'new_language': lang,
                'new_confidence': conf,
                'match_score': metadata.get('match_score', 0),
                'query_used': metadata.get('query_used', ''),
                'jiosaavn_title': metadata.get('jiosaavn_title', ''),
                'jiosaavn_subtitle': metadata.get('jiosaavn_subtitle', ''),
                'detection_method': 'batch3_api_keyword',
                'verified_by_batch2': 'NO'
            }
            
            # Check if Batch 2 agrees with this result
            if file_path in batch2_results:
                batch2_lang = batch2_results[file_path]['language']
                batch2_conf = batch2_results[file_path]['confidence']
                
                if batch2_lang == lang:
                    # BOTH AGREE! Mark as FINAL VERIFIED
                    result['verified_by_batch2'] = 'YES'
                    result['batch2_confidence'] = batch2_conf
                    result['batch2_method'] = batch2_results[file_path]['method']
                    result['final_confidence'] = max(conf, batch2_conf)
                    result['verified_status'] = 'CONFIRMED'
                    result['is_verified'] = True  # Flag for counting
                    
                    # Store update for main dataframe
                    update = {
                        'detected_language': lang,
                        'confidence': max(conf, batch2_conf),
                        'status': 'confirmed_batch2_batch3',
                        'needs_ai': False
                    }
                    return result, file_path, update
                else:
                    # Disagree - need manual review
                    result['verified_by_batch2'] = 'CONFLICT'
                    result['batch2_language'] = batch2_lang
                    result['batch2_confidence'] = batch2_conf
                    result['verified_status'] = 'NEEDS_REVIEW'
                    return result, file_path, None
            else:
                # Only Batch 3 detected, no Batch 2 comparison
                result['verified_status'] = 'BATCH3_ONLY'
                
                # Still update main CSV with Batch 3 result
                update = {
                    'detected_language': lang,
                    'confidence': conf,
                    'status': 'confident_batch3_api',
                    'needs_ai': False
                }
                return result, file_path, update
        
        return None, None, None
    
    # Process songs in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_song, row): idx for idx, row in low_conf.iterrows()}
        
        with tqdm(total=len(low_conf), desc="API Search") as pbar:
            for future in as_completed(futures):
                result, file_path, update = future.result()
                if result:
                    improved_count += 1
                    batch3_results.append(result)
                    
                    if result.get('is_verified'):
                        verified_count += 1
                        final_verified.append(result)
                    
                    if update and file_path:
                        updates_map[file_path] = update
                
                pbar.update(1)
    
    # Save Batch 3 results
    if batch3_results:
        df_batch3 = pd.DataFrame(batch3_results)
        df_batch3.to_csv(OUTPUT_CSV, index=False)
        print(f"\n✅ Batch 3 Complete: {improved_count} songs detected!")
        print(f"📄 Results saved: {OUTPUT_CSV}")
        
        # Update main language_report.csv with verified results
        if updates_map:
            print(f"\n🔄 Updating main CSV with {len(updates_map)} confirmed detections...")
            
            # Apply updates to main dataframe
            for file_path, update_dict in updates_map.items():
                mask = df_main['file_path'] == file_path
                for col, value in update_dict.items():
                    if col in df_main.columns:
                        df_main.loc[mask, col] = value
            
            # Save updated main CSV
            df_main.to_csv(UPDATED_REPORT_CSV, index=False)
            print(f"✅ Updated CSV saved: {UPDATED_REPORT_CSV}")
            print(f"   This contains ALL songs with Batch 3 updates applied!")
        
        # Statistics
        print(f"\n📊 Batch 3 Statistics:")
        print(f"   Total processed: {len(low_conf)}")
        print(f"   Improved by Batch 3: {improved_count}")
        print(f"   Verified by Batch 2: {verified_count} (CONFIRMED)")
        print(f"   Conflicts (need review): {len([r for r in batch3_results if r.get('verified_status') == 'NEEDS_REVIEW'])}")
        print(f"   Batch 3 only: {len([r for r in batch3_results if r.get('verified_status') == 'BATCH3_ONLY'])}")
        print(f"   Still need AI: {len(low_conf) - improved_count}")
        
        # Language distribution
        print(f"\n🌍 Detected Languages (Batch 3):")
        lang_dist = df_batch3['new_language'].value_counts()
        for lang, count in lang_dist.items():
            print(f"   {lang}: {count} songs")
        
        # Verification status
        if 'verified_status' in df_batch3.columns:
            print(f"\n✔️ Verification Status:")
            status_dist = df_batch3['verified_status'].value_counts()
            for status, count in status_dist.items():
                print(f"   {status}: {count} songs")
        
        # Show sample verified matches
        if final_verified:
            print(f"\n📝 Sample Verified Songs (Both methods agree):")
            for i, row in enumerate(df_final.head(5).iterrows(), 1):
                r = row[1]
                print(f"   {i}. {r['file_name'][:50]}...")
                print(f"      Language: {r['new_language']}")
                print(f"      Batch 2: {r['batch2_confidence']:.2f} ({r['batch2_method']})")
                print(f"      Batch 3: {r['new_confidence']:.2f} (API keyword)")
                print(f"      Final Confidence: {r['final_confidence']:.2f}")
                print()
    else:
        print("\n⚠️ No improvements found using API keyword search.")

if __name__ == "__main__":
    process_batch3()
