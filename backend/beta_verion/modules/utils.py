"""Utility functions for filename sanitization and formatting"""
import re
import os


def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    # Remove invalid characters
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
        
    # Replace forward slash with space
    filename = filename.replace('/', ' ')
    filename = filename.replace('\\', ' ')
    
    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Collapse multiple spaces
    filename = re.sub(r'\s+', ' ', filename)
    
    # Trim dots and spaces
    filename = filename.strip('. ')
    
    # Default if empty
    if not filename:
        filename = 'Unknown'
        
    return filename


def build_filename(metadata, template='{artist} - {title}', ext='.flac'):
    """Build filename from metadata and template"""
    # Sanitize metadata fields
    title = sanitize_filename(metadata.get('title', 'Unknown'))
    artist = sanitize_filename(metadata.get('artist', 'Unknown'))
    album = sanitize_filename(metadata.get('album', 'Unknown'))
    album_artist = sanitize_filename(metadata.get('album_artist', artist))
    
    # Extract year
    year = metadata.get('release_date', '')[:4] if metadata.get('release_date') else ''
    
    # Track/Disc numbers
    track = metadata.get('track_number', 0)
    disc = metadata.get('disc_number', 0)
    
    # Replace placeholders
    filename = template
    filename = filename.replace('{title}', title)
    filename = filename.replace('{artist}', artist)
    filename = filename.replace('{album}', album)
    filename = filename.replace('{album_artist}', album_artist)
    filename = filename.replace('{year}', year)
    
    if track:
        filename = filename.replace('{track}', f'{track:02d}')
    else:
        # Remove track placeholder if not available
        filename = re.sub(r'\{track\}\.\s*', '', filename)
        filename = re.sub(r'\{track\}\s*[-\s]*', '', filename)
        
    if disc:
        filename = filename.replace('{disc}', str(disc))
    else:
        filename = re.sub(r'\{disc\}\s*', '', filename)
        
    # Add extension
    if not filename.endswith(ext):
        filename += ext
        
    return filename


def ensure_directory(path):
    """Create directory if it doesn't exist"""
    os.makedirs(path, exist_ok=True)


def format_duration(duration_ms):
    """Convert milliseconds to MM:SS format"""
    seconds = duration_ms // 1000
    minutes = seconds // 60
    seconds = seconds % 60
    return f'{minutes}:{seconds:02d}'


if __name__ == '__main__':
    # Test
    test_metadata = {
        'title': 'Test Song: Special*Edition',
        'artist': 'Artist/Name',
        'album': 'Test<Album>',
        'track_number': 5
    }
    filename = build_filename(test_metadata, '{track}. {artist} - {title}')
    print(f"Generated filename: {filename}")
