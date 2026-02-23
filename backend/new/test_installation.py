"""Test script to verify SpotiFLAC Python installation"""
import sys

print("=" * 60)
print("SpotiFLAC Python - Installation Test")
print("=" * 60)

print("\n[1/6] Checking Python version...")
if sys.version_info >= (3, 8):
    print(f"  ✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
else:
    print(f"  ✗ Python {sys.version_info.major}.{sys.version_info.minor} (3.8+ required)")
    sys.exit(1)

print("\n[2/6] Checking required packages...")
required_packages = {
    'requests': 'HTTP client',
    'mutagen': 'Audio metadata',
    'pyotp': 'TOTP generation',
    'PIL': 'Image processing (Pillow)',
    'click': 'CLI framework',
    'tqdm': 'Progress bars'
}

missing = []
for package, description in required_packages.items():
    try:
        __import__(package)
        print(f"  ✓ {package:15} ({description})")
    except ImportError:
        print(f"  ✗ {package:15} ({description}) - MISSING")
        missing.append(package)

if missing:
    print(f"\n  Install missing packages: pip install {' '.join(missing)}")
    sys.exit(1)

print("\n[3/6] Checking FFmpeg...")
import subprocess
try:
    result = subprocess.run(['ffmpeg', '-version'],
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          timeout=5)
    if result.returncode == 0:
        version_line = result.stdout.decode().split('\n')[0]
        print(f"  ✓ FFmpeg installed: {version_line}")
    else:
        print("  ⚠ FFmpeg found but may not work correctly")
except (FileNotFoundError, subprocess.TimeoutExpired):
    print("  ⚠ FFmpeg not found (required for Amazon Music)")
    print("    Install from: https://ffmpeg.org/download.html")

print("\n[4/6] Testing module imports...")
try:
    from modules import spotify, songlink, tidal, qobuz, amazon, metadata, utils
    print("  ✓ All modules imported successfully")
except ImportError as e:
    print(f"  ✗ Module import failed: {e}")
    sys.exit(1)

print("\n[5/6] Checking configuration...")
try:
    import config
    print(f"  ✓ Tidal APIs: {len(config.TIDAL_APIS)} configured")
    print(f"  ✓ Qobuz APIs: {len(config.QOBUZ_STANDARD_APIS)} configured")
    print(f"  ✓ Default output: {config.DEFAULT_OUTPUT_DIR}")
except Exception as e:
    print(f"  ✗ Configuration error: {e}")
    sys.exit(1)

print("\n[6/6] Testing file system...")
import os
try:
    test_dir = config.DEFAULT_OUTPUT_DIR
    os.makedirs(test_dir, exist_ok=True)
    print(f"  ✓ Can create output directory: {test_dir}")
except Exception as e:
    print(f"  ✗ Cannot create output directory: {e}")

print("\n" + "=" * 60)
print("✓ Installation test complete!")
print("\nYou're ready to use SpotiFLAC Python!")
print("\nQuick start:")
print('  python main.py "https://open.spotify.com/track/30zuTmjdAFAeZJkYAbdLSy?si=cc9ff623f5be4ba8"')
print("\nFor more help:")
print("  python main.py --help")
print("  See QUICKSTART.md for examples")
print("=" * 60)
