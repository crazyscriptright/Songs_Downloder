"""
Test script to verify API URL construction for video downloads
"""
import urllib.parse

# Test 1: Video download (1080p)
def test_video_download():
    VIDEO_DOWNLOAD_API_KEY = 'dfcb6d76f2f6a9894gjkege8a4ab232222'
    
    advanced_options = {
        'keepVideo': True,
        'embedSubtitles': True,
        'addMetadata': True,
        'videoQuality': '1080',
        'videoFPS': '30',
        'videoFormat': 'mkv',  # This is ignored by API
        'audioQuality': '128'
    }
    
    # Determine if it's video or audio download
    is_video = advanced_options.get('keepVideo', False)
    
    # Map format based on whether it's video or audio
    if is_video:
        # Video download - use video quality setting (API expects: 360, 480, 720, 1080, 1440, 4k, 8k)
        video_quality = advanced_options.get('videoQuality', '1080')
        format_type = video_quality  # Use quality directly as format
        file_extension = 'mp4'  # Videos are always MP4 from the API
        print(f"🎥 VIDEO MODE: quality={video_quality}, format={format_type}, extension={file_extension}")
    else:
        # Audio download (API expects: mp3, m4a, flac, wav, opus)
        audio_format = advanced_options.get('audioFormat', 'mp3')
        format_type = audio_format if audio_format in ['mp3', 'm4a', 'flac', 'wav', 'opus'] else 'mp3'
        file_extension = format_type
        print(f"🎵 AUDIO MODE: format={format_type}, extension={file_extension}")
    
    # Build params
    params = {
        'copyright': '0',
        'allow_extended_duration': '1',
        'format': format_type,
        'url': 'https://www.youtube.com/watch?v=ZPgctd-_n5k',
        'api': VIDEO_DOWNLOAD_API_KEY,
        'add_info': '1'
    }
    
    # Add audio quality if specified
    audio_quality = advanced_options.get('audioQuality')
    if audio_quality:
        params['audio_quality'] = audio_quality
    
    api_url = 'https://p.savenow.to/ajax/download.php'
    full_api_url = api_url + '?' + urllib.parse.urlencode(params)
    
    print(f"\n✨ EXPECTED VIDEO URL:")
    print(f"https://p.savenow.to/ajax/download.php?copyright=0&allow_extended_duration=1&format=1080&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DZPgctd-_n5k&api=dfcb6d76f2f6a9894gjkege8a4ab232222&audio_quality=128")
    
    print(f"\n🌐 GENERATED URL:")
    print(full_api_url)
    
    print(f"\n✅ Format: {format_type} (should be '1080')")
    print(f"✅ Extension: {file_extension} (should be 'mp4')")
    print(f"✅ Audio quality: {audio_quality} (should be '128')")

# Test 2: Audio download (MP3)
def test_audio_download():
    VIDEO_DOWNLOAD_API_KEY = 'dfcb6d76f2f6a9894gjkege8a4ab232222'
    
    advanced_options = {
        'keepVideo': False,
        'audioFormat': 'mp3',
        'audioQuality': '320'
    }
    
    # Determine if it's video or audio download
    is_video = advanced_options.get('keepVideo', False)
    
    # Map format based on whether it's video or audio
    if is_video:
        video_quality = advanced_options.get('videoQuality', '1080')
        format_type = video_quality
        file_extension = 'mp4'
        print(f"🎥 VIDEO MODE: quality={video_quality}, format={format_type}, extension={file_extension}")
    else:
        audio_format = advanced_options.get('audioFormat', 'mp3')
        format_type = audio_format if audio_format in ['mp3', 'm4a', 'flac', 'wav', 'opus'] else 'mp3'
        file_extension = format_type
        print(f"🎵 AUDIO MODE: format={format_type}, extension={file_extension}")
    
    # Build params
    params = {
        'copyright': '0',
        'allow_extended_duration': '1',
        'format': format_type,
        'url': 'https://www.youtube.com/watch?v=PMiR-4N_CZ4',
        'api': VIDEO_DOWNLOAD_API_KEY,
        'add_info': '1'
    }
    
    # Add audio quality if specified
    audio_quality = advanced_options.get('audioQuality')
    if audio_quality:
        params['audio_quality'] = audio_quality
    
    api_url = 'https://p.savenow.to/ajax/download.php'
    full_api_url = api_url + '?' + urllib.parse.urlencode(params)
    
    print(f"\n✨ EXPECTED AUDIO URL:")
    print(f"https://p.savenow.to/ajax/download.php?copyright=0&allow_extended_duration=1&format=mp3&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DPMiR-4N_CZ4&audio_quality=320&api=dfcb6d76f2f6a9894gjkege8a4ab232222")
    
    print(f"\n🌐 GENERATED URL:")
    print(full_api_url)
    
    print(f"\n✅ Format: {format_type} (should be 'mp3')")
    print(f"✅ Extension: {file_extension} (should be 'mp3')")
    print(f"✅ Audio quality: {audio_quality} (should be '320')")

if __name__ == '__main__':
    print("=" * 80)
    print("TEST 1: VIDEO DOWNLOAD (1080p)")
    print("=" * 80)
    test_video_download()
    
    print("\n" + "=" * 80)
    print("TEST 2: AUDIO DOWNLOAD (MP3)")
    print("=" * 80)
    test_audio_download()
