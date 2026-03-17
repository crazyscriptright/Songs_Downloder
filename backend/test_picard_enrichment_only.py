#!/usr/bin/env python3
"""
Test Picard enrichment ONLY (skip primary enrichment).

This bypasses all primary enrichment and runs ONLY Picard fallback.
Useful for testing Picard's effectiveness on a single file.

Usage:
    # Test Picard-only enrichment
    python test_picard_enrichment_only.py "path/to/song.mp3"
    
    # With artist+title (for testing without file)
    python test_picard_enrichment_only.py "7 Years" --artist "Lukas Graham"
    
    # Multiple songs
    python test_picard_enrichment_only.py "path/to/folder" --recursive
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Import Picard enricher
try:
    from picard_fallback_enricher import (
        run_picard_fallback_enrichment,
        install_requirements,
        is_enrichment_complete
    )
    PICARD_AVAILABLE = install_requirements()
except ImportError:
    PICARD_AVAILABLE = False
    logger.error("❌ Picard enricher not available. Install with: pip install musicbrainzngs pyacoustid")
    sys.exit(1)

# Import metadata reader
from enrich_metadata import read_existing_metadata


def test_picard_only_on_file(file_path: Path) -> Dict[str, Any]:
    """
    Test Picard enrichment ONLY on a single file.
    
    This creates incomplete metadata on purpose so Picard is triggered.
    """
    logger.info("\n" + "="*70)
    logger.info("PICARD-ONLY ENRICHMENT TEST")
    logger.info("="*70)
    logger.info(f"File: {file_path}")
    
    if not file_path.exists():
        logger.error(f"❌ File not found: {file_path}")
        return {}
    
    # Read existing metadata
    logger.info("\n[1/3] Reading file metadata...")
    existing_metadata = read_existing_metadata(file_path)
    
    logger.info(f"   Title: {existing_metadata.get('title', '(empty)')}")
    logger.info(f"   Artist: {existing_metadata.get('artist', '(empty)')}")
    logger.info(f"   Album: {existing_metadata.get('album', '(empty)')}")
    logger.info(f"   Genre: {existing_metadata.get('genre', '(empty)')}")
    logger.info(f"   Date: {existing_metadata.get('date', '(empty)')}")
    
    # Create incomplete metadata to trigger Picard
    logger.info("\n[2/3] Creating incomplete metadata (forcing Picard trigger)...")
    test_metadata = existing_metadata.copy()
    
    # Remove genre and date to force Picard to run
    test_metadata['genre'] = None
    test_metadata['date'] = None
    
    logger.info(f"   Cleared genre and date")
    logger.info(f"   Completeness: {is_enrichment_complete(test_metadata)}")
    
    # Run ONLY Picard enrichment
    logger.info("\n[3/3] Running Picard fallback enrichment...")
    picard_result = run_picard_fallback_enrichment(file_path, test_metadata)
    
    logger.info("\n" + "="*70)
    logger.info("PICARD ENRICHMENT RESULTS")
    logger.info("="*70)
    logger.info(f"Ran: {picard_result['ran']}")
    logger.info(f"Enriched: {picard_result['metadata_enriched']}")
    logger.info(f"Method: {picard_result.get('method', 'N/A')}")
    logger.info(f"Confidence: {picard_result.get('confidence', 0):.2f}")
    logger.info(f"Filled fields: {', '.join(picard_result.get('filled_fields', []))}")
    
    if picard_result['errors']:
        logger.error(f"Errors: {', '.join(picard_result['errors'])}")
    
    # Show what was filled
    if picard_result['metadata_enriched']:
        logger.info("\n✅ Picard successfully enriched:")
        for field in picard_result.get('filled_fields', []):
            value = test_metadata.get(field, 'N/A')
            logger.info(f"   {field}: {value}")
    else:
        logger.warning("⚠️  Picard did not enrich the file")
    
    return test_metadata


def test_picard_only_with_metadata(title: str, artist: str, album: str = '') -> Dict[str, Any]:
    """
    Test Picard enrichment with metadata only (no file needed).
    
    Useful for quick testing without actual audio file.
    """
    logger.info("\n" + "="*70)
    logger.info("PICARD-ONLY ENRICHMENT TEST (Metadata Only)")
    logger.info("="*70)
    
    # Create metadata
    test_metadata = {
        'title': title,
        'artist': artist,
        'album': album,
        'genre': None,
        'date': None,
        'duration_ms': 0
    }
    
    logger.info(f"Title: {title}")
    logger.info(f"Artist: {artist}")
    logger.info(f"Album: {album}")
    logger.info(f"Completeness: {is_enrichment_complete(test_metadata)}")
    
    # Create dummy file path (won't be used since AcoustID won't work)
    dummy_file = Path(__file__).parent / "dummy.mp3"
    
    logger.info("\n[1/1] Running Picard fallback enrichment...")
    picard_result = run_picard_fallback_enrichment(dummy_file, test_metadata)
    
    logger.info("\n" + "="*70)
    logger.info("PICARD ENRICHMENT RESULTS")
    logger.info("="*70)
    logger.info(f"Ran: {picard_result['ran']}")
    logger.info(f"Enriched: {picard_result['metadata_enriched']}")
    logger.info(f"Method: {picard_result.get('method', 'N/A')}")
    logger.info(f"Confidence: {picard_result.get('confidence', 0):.2f}")
    logger.info(f"Filled fields: {', '.join(picard_result.get('filled_fields', []))}")
    
    if picard_result['errors']:
        logger.error(f"Errors: {', '.join(picard_result['errors'])}")
    
    # Show what was filled
    if picard_result['metadata_enriched']:
        logger.info("\n✅ Picard successfully enriched:")
        for field in picard_result.get('filled_fields', []):
            value = test_metadata.get(field, 'N/A')
            logger.info(f"   {field}: {value}")
    else:
        logger.warning("⚠️  Picard did not enrich the metadata")
    
    return test_metadata


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExamples:")
        print('  python test_picard_enrichment_only.py "C:\\music\\song.mp3"')
        print('  python test_picard_enrichment_only.py "7 Years" --artist "Lukas Graham"')
        print('  python test_picard_enrichment_only.py "C:\\music\\All" --recursive')
        sys.exit(1)
    
    # Check if Picard is available
    if not PICARD_AVAILABLE:
        logger.error("❌ Picard libraries not available")
        logger.error("   Install with: pip install musicbrainzngs pyacoustid")
        sys.exit(1)
    
    first_arg = sys.argv[1]
    
    # Mode 1: Test with file path
    if Path(first_arg).exists():
        file_path = Path(first_arg)
        
        if file_path.is_file():
            # Test single file
            test_picard_only_on_file(file_path)
        
        elif file_path.is_dir() and '--recursive' in sys.argv:
            # Test folder recursively
            audio_extensions = {'.mp3', '.flac', '.m4a', '.mp4', '.aac'}
            audio_files = [f for f in file_path.rglob('*') if f.suffix.lower() in audio_extensions]
            
            logger.info(f"\n📁 Found {len(audio_files)} audio files")
            
            for idx, audio_file in enumerate(audio_files, 1):
                logger.info(f"\n{'='*70}")
                logger.info(f"[{idx}/{len(audio_files)}] Testing {audio_file.name}")
                logger.info(f"{'='*70}")
                test_picard_only_on_file(audio_file)
    
    # Mode 2: Test with metadata only (title + artist)
    elif '--artist' in sys.argv:
        title = first_arg
        try:
            artist_idx = sys.argv.index('--artist')
            artist = sys.argv[artist_idx + 1]
            album = ''
            
            if '--album' in sys.argv:
                album_idx = sys.argv.index('--album')
                album = sys.argv[album_idx + 1]
            
            test_picard_only_with_metadata(title, artist, album)
        
        except (IndexError, ValueError):
            logger.error("Invalid arguments for --artist")
            sys.exit(1)
    
    else:
        logger.error(f"❌ File not found: {first_arg}")
        sys.exit(1)


if __name__ == '__main__':
    main()
