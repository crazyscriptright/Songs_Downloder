"""SpotiFLAC Python - Download music in FLAC from multiple platforms"""
import os
import sys
import click
from modules import spotify, songlink, tidal, qobuz, amazon, metadata, utils, url_detector
from config import DEFAULT_OUTPUT_DIR, DEFAULT_SERVICE, DEFAULT_QUALITY, SPOTDL_ENABLED

if SPOTDL_ENABLED:
    try:
        from modules import spotdl
        SPOTDL_AVAILABLE = True
    except ImportError:
        SPOTDL_AVAILABLE = False
        print("⚠ SpotDL not installed. Install with: pip install spotdl")
else:
    SPOTDL_AVAILABLE = False

@click.command()
@click.argument('music_url')
@click.option('--service', '-s', default=DEFAULT_SERVICE,
              type=click.Choice(['auto', 'tidal', 'qobuz', 'amazon', 'spotdl'], case_sensitive=False),
              help='Streaming service to use (auto = detect from URL or try all)')
@click.option('--quality', '-q', default=DEFAULT_QUALITY,
              help='Audio quality (HI_RES, LOSSLESS, or 6/7/27 for Qobuz)')
@click.option('--output', '-o', default=DEFAULT_OUTPUT_DIR,
              help='Output directory')
@click.option('--template', '-t', default='{artist} - {title}',
              help='Filename template (use {title}, {artist}, {album}, {track}, etc.)')
@click.option('--fallback/--no-fallback', default=True,
              help='Enable/disable fallback to other services')
def download(music_url, service, quality, output, template, fallback):
    """Download music in FLAC format from Spotify, Tidal, Qobuz, Amazon, or YouTube

    Examples:

        python main.py "https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp"

        python main.py "https://tidal.com/browse/track/123456789"

        python main.py "https://www.qobuz.com/us-en/album/name/id"

        python main.py "https://music.amazon.com/albums/B08X123456"

        python main.py "SPOTIFY_URL" --service qobuz

        python main.py "SPOTIFY_URL" --service spotdl
    """
    try:

        detector = url_detector.URLDetector()
        detected_platform, track_id = detector.get_track_id(music_url)

        if not detected_platform:
            raise Exception("Unsupported URL format. Supported: Spotify, Tidal, Qobuz, Amazon")

        print(f"\nDetected Platform: {detected_platform.capitalize()}")

        if service == 'auto':

            if detected_platform != 'spotify':
                service = detected_platform
                print(f"Auto-selected service: {service}")
            else:

                service = 'tidal'
                print(f"Auto-selected service: {service} (fallback enabled)")

        if detected_platform != 'spotify' and service == detected_platform:
            return download_direct(music_url, detected_platform, track_id, output, template, quality)

        if detected_platform == 'spotify':
            if not track_id:
                raise Exception("Could not extract track ID from Spotify URL")
            print(f"Spotify Track ID: {track_id}")

        print("\n[1/4] Fetching Spotify metadata...")
        spotify_client = spotify.SpotifyClient()
        track_metadata = spotify_client.get_track_metadata(track_id)

        print(f"  Title: {track_metadata['title']}")
        print(f"  Artist: {track_metadata['artist']}")
        print(f"  Album: {track_metadata['album']}")
        print(f"  Duration: {utils.format_duration(track_metadata['duration_ms'])}")

        print(f"\n[2/4] Converting to {service.capitalize()} URL...")
        songlink_client = songlink.SongLinkClient()

        if service == 'amazon':
            ext = '.m4a'
        else:
            ext = '.flac'

        filename = utils.build_filename(track_metadata, template, ext)
        utils.ensure_directory(output)
        output_path = os.path.join(output, filename)

        if os.path.exists(output_path):
            print(f"\n✓ File already exists: {output_path}")
            return

        print(f"\n[3/4] Downloading from {service.capitalize()}...")

        download_success = False
        services_to_try = [service]

        if fallback and service != 'spotdl':
            all_services = ['tidal', 'qobuz', 'amazon']
            if SPOTDL_AVAILABLE:
                all_services.append('spotdl')

            services_to_try.extend([s for s in all_services if s != service])

        last_error = None
        for current_service in services_to_try:
            try:
                print(f"\nTrying {current_service.capitalize()}...")

                '''if current_service == 'tidal':
                    service_url = songlink_client.get_platform_url(track_id, 'tidal')
                    downloader = tidal.TidalDownloader()
                    downloader.download(service_url, output_path, quality)
                    download_success = True
                    break

                elif current_service == 'qobuz':
                    isrc = songlink_client.get_isrc(track_id)
                    if not isrc:
                        raise Exception("ISRC not found - cannot search Qobuz")
                    downloader = qobuz.QobuzDownloader()
                    downloader.download(isrc, output_path, quality)
                    download_success = True
                    break

                elif current_service == 'amazon':
                    service_url = songlink_client.get_platform_url(track_id, 'amazonMusic')
                    downloader = amazon.AmazonDownloader()
                    downloader.download(service_url, output_path)
                    download_success = True
                    break'''

                if current_service == 'spotdl':
                    if not SPOTDL_AVAILABLE:
                        raise Exception("SpotDL not installed")
                    downloader = spotdl.SpotDLDownloader()
                    format = 'flac' if ext == '.flac' else 'mp3'
                    downloader.download_with_metadata(music_url, output_path, track_metadata)
                    download_success = True
                    break

            except Exception as e:
                last_error = e
                print(f"✗ {current_service.capitalize()} failed: {e}")
                if not fallback or current_service == services_to_try[-1]:

                    break
                continue

        if not download_success:
            raise Exception(f"All services failed. Last error: {last_error}")

        print("\n[4/4] Embedding metadata...")
        metadata.embed_metadata(output_path, track_metadata)

        print("\n" + "=" * 60)
        print(f"✓ Download complete!")
        print(f"  File: {output_path}")
        print(f"  Size: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n⚠ Download cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

def download_direct(url, platform, track_id, output_dir, template, quality):
    """Download directly from Tidal/Qobuz/Amazon URL"""
    print(f"\n[Direct Download Mode - {platform.capitalize()}]")

    try:

        print("\n[1/3] Attempting to fetch Spotify metadata...")
        track_metadata = None
        try:
            songlink_client = songlink.SongLinkClient()

            print("  (Skipping - using platform's own metadata)")
        except:
            pass

        if not track_metadata:

            filename = f"{platform}_{track_id}.flac"
            if platform == 'amazon':
                filename = f"{platform}_{track_id}.m4a"
        else:
            ext = '.m4a' if platform == 'amazon' else '.flac'
            filename = utils.build_filename(track_metadata, template, ext)

        utils.ensure_directory(output_dir)
        output_path = os.path.join(output_dir, filename)

        if os.path.exists(output_path):
            print(f"\n✓ File already exists: {output_path}")
            return

        print(f"\n[2/3] Downloading from {platform.capitalize()}...")

        if platform == 'tidal':
            downloader = tidal.TidalDownloader()
            downloader.download(url, output_path, quality)

        elif platform == 'qobuz':
            print("⚠ Direct Qobuz downloads require ISRC or track ID")
            print("  Using Qobuz downloader...")
            downloader = qobuz.QobuzDownloader()

            download_url = downloader.get_download_url(track_id, quality)
            downloader.download_file(download_url, output_path)

        elif platform == 'amazon':
            downloader = amazon.AmazonDownloader()
            downloader.download(url, output_path)

        print(f"\n[3/3] Embedding metadata...")
        if track_metadata:
            metadata.embed_metadata(output_path, track_metadata)
        else:
            print("  (No Spotify metadata available - using platform metadata)")

        print("\n" + "=" * 60)
        print(f"✓ Download complete!")
        print(f"  File: {output_path}")
        if os.path.exists(output_path):
            print(f"  Size: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Direct download failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    download()
