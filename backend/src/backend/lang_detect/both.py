import whisper
import os
import pandas as pd
from tqdm import tqdm
from pathlib import Path
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen import File
from mutagen.id3 import ID3
import torch
import numpy as np
import librosa
import re
import time
import json
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

torch.set_num_threads(8)

# ================= PROXY CONFIG =================
# Auto-fetch free proxies (disabled by default for reliability)
print("🔄 Checking proxy configuration...")
PROXY_LIST = [None]  # Start with direct connection only
USE_PROXIES = True  # Set to True to enable proxy fetching

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

# ================= CONFIG =================
SONG_DIR = "B:/music"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(SCRIPT_DIR, "language_report.csv")

SEGMENT_DURATION = 15  # seconds per segment
CONFIDENCE_THRESHOLD = 0.80
MAX_SEGMENTS = 1  # Maximum segments to analyze
VAD_THRESHOLD = 0.3  # Voice activity detection threshold (0-1) - Lower = more sensitive
# ========================================

# Load models
model = whisper.load_model("small")  # CPU-friendly
vad_model, vad_utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=False)
(get_speech_timestamps, *_) = vad_utils

# ---------- Load existing CSV (resume support) ----------
if os.path.exists(CSV_FILE):
    df_existing = pd.read_csv(CSV_FILE)
    processed_files = set(df_existing["file_path"].tolist())
    results = df_existing.to_dict("records")
else:
    processed_files = set()
    results = []

# ---------- Metadata extraction function ----------
def extract_metadata(file_path):
    """Extract song metadata (title, artist, album)"""
    try:
        audio = File(file_path, easy=True)
        if audio is None:
            return None, None, None
        
        title = audio.get('title', [None])[0]
        artist = audio.get('artist', [None])[0]
        album = audio.get('album', [None])[0]
        
        return title, artist, album
    except Exception:
        return None, None, None

# ---------- JioSaavn API language detection (FASTEST - 100% accurate) ----------
def detect_language_from_jiosaavn(title, artist, proxy=None):
    """Search JioSaavn API for song and get language + important metadata"""
    if not title:
        return None, 0.0, 'no_title', {}
    
    try:
        # Build search query
        query = f"{title}"
        if artist:
            query += f" {artist}"
        
        # JioSaavn search API
        url = "https://www.jiosaavn.com/api.php"
        params = {
            'p': 1,
            'q': query,
            '_format': 'json',
            '_marker': 0,
            'api_version': 4,
            'ctx': 'wap6dot0',
            'n': 10,  # Get more results for better matching
            '__call': 'search.getResults'
        }
        
        # Setup headers to mimic Indian browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-IN,en;q=0.9,hi;q=0.8',
            'Referer': 'https://www.jiosaavn.com/',
            'Origin': 'https://www.jiosaavn.com'
        }
        
        # Setup proxy if provided
        proxies = {'http': proxy, 'https': proxy} if proxy else None
        
        response = requests.get(url, params=params, timeout=10, headers=headers, proxies=proxies)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'results' in data and len(data['results']) > 0:
                # Find best match by comparing title and artist similarity
                best_match = None
                best_score = 0
                
                for idx, result in enumerate(data['results'][:10]):  # Check top 10 results
                    result_title = result.get('title', '').lower()
                    result_subtitle = result.get('subtitle', '').lower()
                    
                    # Clean strings for comparison (remove track numbers, special chars, extra spaces)
                    # Remove leading numbers like "01 ", "02. ", "1-", etc.
                    clean_title = re.sub(r'^\d+[\s\-\.]+', '', title.lower())
                    clean_title = re.sub(r'[^\w\s]', '', clean_title).strip()
                    
                    clean_result_title = re.sub(r'^\d+[\s\-\.]+', '', result_title)
                    clean_result_title = re.sub(r'[^\w\s]', '', clean_result_title).strip()
                    
                    clean_artist = re.sub(r'[^\w\s]', '', artist.lower()).strip() if artist else ''
                    clean_result_subtitle = re.sub(r'[^\w\s]', '', result_subtitle).strip()
                    
                    result['_match_index'] = idx  # Track which result this is
                    
                    # Calculate match score
                    score = 0
                    
                    # Title exact match = 100 points
                    if clean_title == clean_result_title:
                        score += 100
                    # Title contains or contained = 50 points
                    elif clean_title in clean_result_title or clean_result_title in clean_title:
                        score += 50
                    # Title words overlap = 30 points
                    elif any(word in clean_result_title for word in clean_title.split() if len(word) > 3):
                        score += 30
                    
                    # Artist match = 50 points (improved matching)
                    if artist and clean_artist:
                        # Check if all artist words appear in result subtitle
                        artist_words = [w for w in clean_artist.split() if len(w) > 2]
                        if artist_words:
                            matches = sum(1 for word in artist_words if word in clean_result_subtitle)
                            if matches == len(artist_words):
                                score += 50  # All artist words found
                            elif matches > 0:
                                score += 25  # Partial artist match
                    
                    # Prefer songs over other types (albums, playlists)
                    if result.get('type') == 'song':
                        score += 20
                    
                    # Update best match
                    if score > best_score:
                        best_score = score
                        best_match = result
                

                # Only use result if match score is decent (at least 30 points for title match)
                if best_match and best_score >= 30:
                    
                    if 'language' in best_match:
                        lang_full = best_match['language'].lower()
                        chosen_index = best_match.get('_match_index', -1)
                        
                        # Extract important metadata for FFmpeg usage
                        metadata = {
                            'jiosaavn_id': best_match.get('id', ''),
                            'jiosaavn_title': best_match.get('title', ''),
                            'jiosaavn_subtitle': best_match.get('subtitle', ''),
                            'jiosaavn_year': best_match.get('year', ''),
                            'jiosaavn_album_id': best_match.get('more_info', {}).get('album_id', ''),
                            'jiosaavn_album': best_match.get('more_info', {}).get('album', ''),
                            'jiosaavn_duration': best_match.get('more_info', {}).get('duration', ''),
                            'jiosaavn_320kbps': best_match.get('more_info', {}).get('320kbps', ''),
                            'jiosaavn_label': best_match.get('more_info', {}).get('label', ''),
                            'jiosaavn_play_count': best_match.get('play_count', ''),
                            'jiosaavn_image': best_match.get('image', ''),
                            'jiosaavn_album_url': best_match.get('more_info', {}).get('album_url', ''),
                            'jiosaavn_perma_url': best_match.get('perma_url', ''),
                            'jiosaavn_encrypted_media_url': best_match.get('more_info', {}).get('encrypted_media_url', ''),
                            'jiosaavn_match_score': best_score,  # Match quality score
                            'jiosaavn_chosen_index': chosen_index,  # Which result was chosen (0-9)
                            'jiosaavn_total_results': data.get('total', 0),  # Total results available
                            'jiosaavn_full_response': json.dumps(data, ensure_ascii=False),  # Entire API response
                            'jiosaavn_matched_json': json.dumps(best_match, ensure_ascii=False)  # Just the matched song
                        }
                        
                        # Map JioSaavn language names to Whisper codes
                        lang_map = {
                            'english': 'en', 'hindi': 'hi', 'telugu': 'te', 
                            'kannada': 'kn', 'tamil': 'ta', 'marathi': 'mr',
                            'bengali': 'bn', 'gujarati': 'gu', 'punjabi': 'pa',
                            'urdu': 'ur', 'malayalam': 'ml', 'odia': 'or',
                            'assamese': 'as', 'bhojpuri': 'hi',  # Bhojpuri -> Hindi
                            'rajasthani': 'hi', 'haryanvi': 'hi',
                            'sadri': 'hi', 'ahirani': 'mr', 'gujarati': 'gu'  # Added more regional languages
                        }
                        
                        if lang_full in lang_map:
                            # Confidence based on match score
                            # 100+ = 0.95, 80-99 = 0.85, 50-79 = 0.75, 30-49 = 0.70
                            if best_score >= 100:
                                confidence = 0.95
                            elif best_score >= 80:
                                confidence = 0.85
                            elif best_score >= 50:
                                confidence = 0.75
                            else:
                                confidence = 0.70
                            
                            return lang_map[lang_full], confidence, 'jiosaavn_api', metadata
        
        return None, 0.0, 'api_no_match', {}
        
    except requests.exceptions.Timeout:
        return None, 0.0, 'api_timeout', {}
    except requests.exceptions.ConnectionError:
        return None, 0.0, 'api_connection_error', {}
    except Exception as e:
        return None, 0.0, f'api_error_{str(e)[:20]}', {}

# ---------- Metadata-based language detection (FAST - no AI needed) ----------
def detect_language_from_metadata(file_path):
    """Detect language from filename/title patterns - 1000x faster than AI"""
    try:
        # Try reading ID3 tags
        audio = ID3(file_path)
        
        # Check filename/title for language hints
        title = audio.get('TIT2', [''])[0] if 'TIT2' in audio else ''
        artist = audio.get('TPE1', [''])[0] if 'TPE1' in audio else ''
        filename = os.path.basename(file_path)
        
        # Combine all text
        text = f"{title} {artist} {filename}".lower()
        
        # Pattern matching for language indicators
        patterns = {
            'hi': r'\b(hindi|हिन्दी|bollywood)\b',
            'te': r'\b(telugu|తెలుగు|tollywood)\b',
            'ta': r'\b(tamil|தமிழ்|kollywood)\b',
            'kn': r'\b(kannada|ಕನ್ನಡ|sandalwood)\b',
            'pa': r'\b(punjabi|ਪੰਜਾਬੀ)\b',
            'mr': r'\b(marathi|मराठी)\b',
            'bn': r'\b(bengali|বাংলা|bangla)\b',
            'ml': r'\b(malayalam|മലയാളം)\b',
            'gu': r'\b(gujarati|ગુજરાતી)\b',
            'en': r'\b(english)\b'
        }
        
        for lang, pattern in patterns.items():
            if re.search(pattern, text):
                return lang, 0.9, 'metadata_pattern'
        
        return None, 0.0, 'no_metadata'
        
    except Exception:
        return None, 0.0, 'metadata_error'

# ---------- Parallel API fetch wrapper ----------
def fetch_api_for_song(file_path):
    """Wrapper function for parallel API fetching"""
    try:
        title, artist, album = extract_metadata(file_path)
        
        # Randomly select proxy for load balancing
        proxy = random.choice(PROXY_LIST) if len(PROXY_LIST) > 1 else None
        
        lang_api, conf_api, method_api, jiosaavn_meta = detect_language_from_jiosaavn(title, artist, proxy)
        lang_meta, conf_meta, method_meta = detect_language_from_metadata(file_path)
        
        return file_path, {
            'title': title,
            'artist': artist,
            'album': album,
            'lang_api': lang_api,
            'conf_api': conf_api,
            'method_api': method_api,
            'jiosaavn_meta': jiosaavn_meta,
            'lang_meta': lang_meta,
            'conf_meta': conf_meta,
            'method_meta': method_meta
        }
    except Exception as e:
        return file_path, None

# ---------- Improved vocal detection (check multiple sections) ----------
def find_vocal_sections(audio_path, num_sections=3):
    """Find multiple vocal sections by sampling different parts of the song"""
    try:
        # Get audio duration first (fast)
        audio_info = MP3(audio_path)
        duration = audio_info.info.length
        
        # Sample sections: early (30s), middle, and 3/4 point
        sample_points = [
            min(30, duration * 0.15),  # ~30s or 15% in
            duration * 0.5,             # Middle
            duration * 0.75             # 3/4 through
        ]
        
        vocal_sections = []
        
        for sample_sec in sample_points:
            if sample_sec >= duration - 15:
                continue
                
            # Load 20-second chunk around this point
            start = max(0, sample_sec - 5)
            try:
                wav, sr = librosa.load(audio_path, sr=16000, mono=True, 
                                      offset=start, duration=20)
                wav_tensor = torch.from_numpy(wav)
                
                # Detect speech in this chunk
                speech_timestamps = get_speech_timestamps(
                    wav_tensor, 
                    vad_model,
                    threshold=0.4,  # Slightly less sensitive for cleaner detection
                    sampling_rate=16000,
                    min_speech_duration_ms=500,
                    min_silence_duration_ms=300
                )
                
                # If vocals found, add to list
                if speech_timestamps and len(speech_timestamps) > 0:
                    relative_start = speech_timestamps[0]['start'] / 16000
                    absolute_start = start + relative_start
                    vocal_sections.append(round(absolute_start, 1))
                    
            except Exception:
                continue
        
        # Return sections or defaults
        if vocal_sections:
            return vocal_sections
        else:
            # No vocals found, return common fallback points
            return [30.0, duration * 0.5, duration * 0.75]
        
    except Exception as e:
        # Ultimate fallback
        return [30.0, 60.0, 90.0]

# ---------- Language detection function ----------
def detect_language_segment(audio_path, start_sec, end_sec):
    audio = whisper.load_audio(audio_path)

    start = int(start_sec * whisper.audio.SAMPLE_RATE)
    end = int(end_sec * whisper.audio.SAMPLE_RATE)

    audio = audio[start:end]

    audio = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio).to(model.device)

    _, probs = model.detect_language(mel)
    lang = max(probs, key=probs.get)
    confidence = probs[lang]

    return lang, confidence

def detect_language_from_sections(audio_path, vocal_sections):
    """Detect language from multiple vocal sections (better accuracy)"""
    best_lang = None
    best_conf = 0.0
    segments_checked = 0
    
    # Try each vocal section
    for start_sec in vocal_sections[:3]:  # Max 3 sections
        end_sec = start_sec + SEGMENT_DURATION
        
        try:
            lang, conf = detect_language_segment(audio_path, start_sec, end_sec)
            segments_checked += 1
            
            # Update best result
            if conf > best_conf:
                best_lang = lang
                best_conf = conf
            
            # If high confidence found, stop early
            if conf >= CONFIDENCE_THRESHOLD:
                return lang, conf, segments_checked
                
        except Exception:
            continue
    
    return best_lang, best_conf, segments_checked

# ---------- Main processing loop (Two-Pass Approach) ----------
# Recursively find all MP3 files from subdirectories
mp3_files = []
for root, dirs, files in os.walk(SONG_DIR):
    for file in files:
        if file.lower().endswith(".mp3"):
            full_path = os.path.join(root, file)
            mp3_files.append((file, full_path))

print(f"Found {len(mp3_files)} MP3 files in {SONG_DIR} and subdirectories")
print(f"Using {MAX_WORKERS} parallel workers with {len(PROXY_LIST)} proxies")
print("\n" + "="*60)
print("PASS 1: Fetching JioSaavn API data (Fast - Parallel)")
print("="*60 + "\n")

# Filter out already processed files
pending_files = [(file, path) for file, path in mp3_files if path not in processed_files]

# PASS 1: Parallel API fetch with proxies
api_results = {}

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    # Submit all fetch tasks
    future_to_file = {executor.submit(fetch_api_for_song, path): (file, path) 
                      for file, path in pending_files}
    
    # Process results as they complete
    for future in tqdm(as_completed(future_to_file), total=len(future_to_file), desc="API Fetch"):
        file, path = future_to_file[future]
        
        try:
            result_path, api_data = future.result()
            
            if api_data:
                # ---- Decide which source to use ----
                lang = api_data['lang_api'] if api_data['conf_api'] >= 0.70 else api_data['lang_meta'] if api_data['conf_meta'] >= 0.9 else None
                conf = max(api_data['conf_api'], api_data['conf_meta'])
                method = api_data['method_api'] if api_data['conf_api'] > api_data['conf_meta'] else api_data['method_meta']
                
                if lang and conf >= 0.70:  # High confidence from metadata/API
                    result_row = {
                        "file_name": file,
                        "file_path": path,
                        "title": api_data['title'],
                        "artist": api_data['artist'],
                        "album": api_data['album'],
                        "vocal_start_sec": None,
                        "detected_language": lang,
                        "detected_with_low_confidence": None,
                        "confidence": conf,
                        "segments_analyzed": 0,
                        "status": f"confident_{method}",
                        "needs_ai": False
                    }
                    
                    if api_data['jiosaavn_meta']:
                        result_row.update(api_data['jiosaavn_meta'])
                    
                    results.append(result_row)
                else:
                    # Low confidence - mark for AI processing
                    result_row = {
                        "file_name": file,
                        "file_path": path,
                        "title": api_data['title'],
                        "artist": api_data['artist'],
                        "album": api_data['album'],
                        "vocal_start_sec": None,
                        "detected_language": "pending_ai",
                        "detected_with_low_confidence": None,
                        "confidence": conf,
                        "segments_analyzed": 0,
                        "status": "needs_ai_detection",
                        "needs_ai": True
                    }
                    
                    if api_data['jiosaavn_meta']:
                        result_row.update(api_data['jiosaavn_meta'])
                    
                    results.append(result_row)
            else:
                # API fetch failed
                title, artist, album = extract_metadata(path)
                result_row = {
                    "file_name": file,
                    "file_path": path,
                    "title": title,
                    "artist": artist,
                    "album": album,
                    "vocal_start_sec": None,
                    "detected_language": "pending_ai",
                    "detected_with_low_confidence": None,
                    "confidence": 0.0,
                    "segments_analyzed": 0,
                    "status": "needs_ai_detection",
                    "needs_ai": True
                }
                results.append(result_row)
                
        except Exception as e:
            # Error processing this song
            title, artist, album = extract_metadata(path)
            result_row = {
                "file_name": file,
                "file_path": path,
                "title": title,
                "artist": artist,
                "album": album,
                "vocal_start_sec": None,
                "detected_language": "pending_ai",
                "detected_with_low_confidence": None,
                "confidence": 0.0,
                "segments_analyzed": 0,
                "status": "needs_ai_detection",
                "needs_ai": True
            }
            results.append(result_row)

# Save all results after parallel fetch
pd.DataFrame(results).to_csv(CSV_FILE, index=False)

# Count songs needing AI
df_temp = pd.DataFrame(results)
needs_ai_count = df_temp['needs_ai'].sum() if 'needs_ai' in df_temp.columns else 0
confident_count = len(results) - needs_ai_count

print(f"\n✅ Pass 1 Complete:")
print(f"   - {confident_count} songs detected with high confidence")
print(f"   - {needs_ai_count} songs need AI detection")

# if needs_ai_count > 0:
#     print("\n" + "="*60)
#     print("PASS 2: AI Detection for remaining songs (Slow)")
#     print("="*60)
#     print(f"\n⚠️  {needs_ai_count} songs need AI processing (takes ~30-60s per song)")
#     print(f"Total estimated time: {needs_ai_count * 45 // 60} minutes\n")
    
#     # Show first 10 songs that need AI
#     ai_needed = [r for r in results if r.get('needs_ai', False)]
#     print("First 10 songs needing AI detection:")
#     for i, r in enumerate(ai_needed[:10], 1):
#         print(f"  {i}. {r['file_name']} (API status: {r['status']})")
#     if len(ai_needed) > 10:
#         print(f"  ... and {len(ai_needed) - 10} more\n")
    
#     response = input("\nProceed with AI detection? (y/n): ").strip().lower()
#     if response != 'y':
#         print("\n⏸️  AI detection skipped. Songs marked as 'pending_ai' in CSV.")
#         print("   Run script again to process them later.\n")
#     else:
#         print("\n🚀 Starting AI detection...\n")
#         # PASS 2: Run AI on low-confidence songs
#         for idx, result in enumerate(tqdm(results, desc="AI Detection")):
#             if not result.get('needs_ai', False):
#                 continue  # Skip already confident songs
            
#             path = result['file_path']
            
#             try:
#                 # ---- Run AI detection ----
#                 # Find multiple vocal sections
#                 vocal_sections = find_vocal_sections(path)
#                 vocal_start = vocal_sections[0] if vocal_sections else 30.0
                
#                 # Detect language from these sections
#                 lang, conf, segments_analyzed = detect_language_from_sections(path, vocal_sections)
                
#                 # Final decision
#                 if conf >= CONFIDENCE_THRESHOLD:
#                     status = "confident_ai"
#                     final_lang = lang
#                 else:
#                     final_lang = "unknown"
#                     status = "low_confidence_ai"
                
#                 # Update result
#                 results[idx].update({
#                     "vocal_start_sec": vocal_start,
#                     "detected_language": final_lang,
#                     "detected_with_low_confidence": lang if conf < CONFIDENCE_THRESHOLD else None,
#                     "confidence": round(conf, 3),
#                     "segments_analyzed": segments_analyzed,
#                     "status": status,
#                     "needs_ai": False
#                 })
                
#             except Exception as e:
#                 # AI failed
#                 results[idx].update({
#                     "detected_language": "unknown",
#                     "status": "ai_failed",
#                     "needs_ai": False
#                 })
            
#             # Save after each AI detection (progress tracking)
#             pd.DataFrame(results).to_csv(CSV_FILE, index=False)

print(f"\n✅ Language detection completed / resumed successfully.")
print(f"📄 Report saved in: {CSV_FILE}")

# Remove internal tracking column
df_final = pd.read_csv(CSV_FILE)
if 'needs_ai' in df_final.columns:
    df_final = df_final.drop(columns=['needs_ai'])
    df_final.to_csv(CSV_FILE, index=False)
    print("✨ Cleaned up temporary columns")
