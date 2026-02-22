"""Example usage and API testing for SpotiFLAC Python"""
from modules import spotify, songlink, utils
import config

def test_spotify_auth():
    """Test Spotify authentication"""
    print("\n" + "=" * 60)
    print("Testing Spotify Authentication")
    print("=" * 60)
    
    try:
        client = spotify.SpotifyClient()
        print("\n[1/3] Generating TOTP...")
        totp_code, version = client.generate_totp()
        print(f"  ✓ TOTP Code: {totp_code} (Version: {version})")
        
        print("\n[2/3] Getting access token...")
        client.get_access_token()
        print(f"  ✓ Access Token: {client.access_token[:30]}...")
        
        print("\n[3/3] Getting client token...")
        client.get_client_token()
        print(f"  ✓ Client Token: {client.client_token[:30]}...")
        
        print("\n✓ Spotify authentication working!")
        return True
        
    except Exception as e:
        print(f"\n✗ Authentication failed: {e}")
        return False


def test_songlink():
    """Test SongLink API"""
    print("\n" + "=" * 60)
    print("Testing SongLink API")
    print("=" * 60)
    
    # Use a well-known track: "Shape of You" by Ed Sheeran
    test_track_id = "7qiZfU4dY1lWllzX7mPBI"
    
    try:
        client = songlink.SongLinkClient()
        
        print(f"\nTest Track ID: {test_track_id}")
        print("\n[1/2] Converting to Tidal URL...")
        tidal_url = client.get_platform_url(test_track_id, 'tidal')
        print(f"  ✓ Tidal URL: {tidal_url}")
        
        print("\n[2/2] Getting ISRC...")
        isrc = client.get_isrc(test_track_id)
        print(f"  ✓ ISRC: {isrc}")
        
        print("\n✓ SongLink API working!")
        return True
        
    except Exception as e:
        print(f"\n✗ SongLink test failed: {e}")
        return False


def test_filename_generation():
    """Test filename generation"""
    print("\n" + "=" * 60)
    print("Testing Filename Generation")
    print("=" * 60)
    
    test_metadata = {
        'title': 'Test Song: Special Edition',
        'artist': 'Artist Name & Friends',
        'album': 'Test Album (Deluxe)',
        'album_artist': 'Various Artists',
        'release_date': '2024-01-15',
        'track_number': 5,
        'disc_number': 1
    }
    
    templates = [
        '{artist} - {title}',
        '{track}. {artist} - {title}',
        '{album_artist} - {album} ({year}) - {track}. {title}',
    ]
    
    print("\nTest metadata:")
    print(f"  Title: {test_metadata['title']}")
    print(f"  Artist: {test_metadata['artist']}")
    print(f"  Track: {test_metadata['track_number']}")
    
    print("\nGenerated filenames:")
    for template in templates:
        filename = utils.build_filename(test_metadata, template)
        print(f"  Template: {template}")
        print(f"  Result:   {filename}\n")
    
    print("✓ Filename generation working!")
    return True


def show_api_status():
    """Show configured APIs"""
    print("\n" + "=" * 60)
    print("Configured API Endpoints")
    print("=" * 60)
    
    print("\nTidal APIs:")
    for i, api in enumerate(config.TIDAL_APIS, 1):
        print(f"  {i}. {api}")
    
    print("\nQobuz APIs:")
    for i, api in enumerate(config.QOBUZ_STANDARD_APIS, 1):
        print(f"  {i}. {api}")
    print(f"  {len(config.QOBUZ_STANDARD_APIS) + 1}. {config.QOBUZ_JUMO_API}")
    
    print("\nAmazon API:")
    print(f"  1. {config.AMAZON_API}")
    
    print("\nSongLink API:")
    print(f"  1. {config.SONGLINK_API}")


def main():
    """Run example tests"""
    print("=" * 60)
    print("SpotiFLAC Python - Example & API Testing")
    print("=" * 60)
    
    # Show configured APIs
    show_api_status()
    
    # Test filename generation (offline test)
    test_filename_generation()
    
    # Ask user if they want to test online features
    print("\n" + "=" * 60)
    response = input("\nTest online APIs? (requires internet) [y/N]: ")
    
    if response.lower() in ['y', 'yes']:
        test_spotify_auth()
        test_songlink()
        
        print("\n" + "=" * 60)
        print("All tests complete!")
        print("\nNext steps:")
        print("  1. Run: python test_installation.py")
        print("  2. Try: python main.py 'SPOTIFY_URL'")
        print("  3. See: QUICKSTART.md for examples")
        print("=" * 60)
    else:
        print("\nSkipped online tests.")
        print("\nTo test with a real download:")
        print("  python main.py 'https://open.spotify.com/track/TRACK_ID'")


if __name__ == '__main__':
    main()
