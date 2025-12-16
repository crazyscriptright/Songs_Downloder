# Quick Test: API Fallback Simulation
# This script helps verify the SIMULATE_YTDLP_ERROR configuration

import os
from dotenv import load_dotenv

print("="*70)
print("🧪 Testing API Fallback Configuration")
print("="*70)

# Load .env file
load_dotenv()

# Check configuration
simulate_error = os.getenv('SIMULATE_YTDLP_ERROR', 'False').lower() == 'true'

print(f"\n📋 Current Configuration:")
print(f"   SIMULATE_YTDLP_ERROR = {os.getenv('SIMULATE_YTDLP_ERROR', 'Not Set')}")
print(f"   Parsed value = {simulate_error}")

if simulate_error:
    print("\n✅ Test mode is ENABLED")
    print("   All YouTube downloads will be simulated to fail and use API fallback")
else:
    print("\n❌ Test mode is DISABLED")
    print("   YouTube downloads will use yt-dlp normally")

print("\n💡 To enable test mode:")
print("   1. Create/edit .env file in backend directory")
print("   2. Add: SIMULATE_YTDLP_ERROR=true")
print("   3. Restart Flask server")

print("\n📚 See TESTING_API_FALLBACK.md for complete guide")
print("="*70)
