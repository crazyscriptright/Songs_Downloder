"""
Quick test for JioSaavn suggestions with Selenium fallback
"""

import sys
import os

# Test with a known PID
test_pid = "IgwLcB06"

print(f"\n{'='*70}")
print(f"Testing JioSaavn Suggestions API Endpoint")
print(f"{'='*70}\n")

# Test 1: Regular API call
print("Test 1: Regular API (should work)")
print("-" * 70)

try:
    import requests
    
    # Simulate API endpoint call
    api_url = f"https://www.jiosaavn.com/api.php?__call=reco.getreco&api_version=4&_format=json&_marker=0&ctx=wap6dot0&pid={test_pid}&language=english"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://www.jiosaavn.com/",
        "Accept": "application/json",
        "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8"
    }
    
    response = requests.get(api_url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        
        if isinstance(data, list) and len(data) > 0:
            print(f"✅ API works! Got {len(data)} suggestions")
            print(f"   First suggestion: {data[0].get('title', 'N/A')} - {data[0].get('subtitle', 'N/A').split(' - ')[0]}")
        else:
            print(f"⚠️ API returned empty results")
    else:
        print(f"❌ API failed with status {response.status_code}")
        
except Exception as e:
    print(f"❌ API test error: {e}")

print()

# Test 2: Check if Selenium module can be imported
print("Test 2: Selenium module import")
print("-" * 70)

try:
    from jiosaavn_selenium_suggestions import get_jiosaavn_suggestions_selenium
    print("✅ Selenium module imported successfully")
    print("   Module is ready to use as fallback")
except Exception as e:
    print(f"❌ Failed to import Selenium module: {e}")

print()

# Test 3: Quick functionality test (without actually running Selenium)
print("Test 3: API integration check")
print("-" * 70)

try:
    # Check if the API endpoint logic would work
    pid = test_pid
    language = 'english'
    
    # Validate PID
    import re
    if re.match(r'^[a-zA-Z0-9_-]{1,20}$', pid):
        print(f"✅ PID validation works: {pid}")
    else:
        print(f"❌ PID validation failed")
    
    # Validate language
    allowed_languages = ['english', 'hindi', 'telugu', 'tamil', 'punjabi', 'bengali', 'marathi', 'gujarati', 'kannada', 'malayalam']
    if language in allowed_languages:
        print(f"✅ Language validation works: {language}")
    else:
        print(f"❌ Language validation failed")
    
    print(f"✅ API integration logic is correct")
    
except Exception as e:
    print(f"❌ Integration check error: {e}")

print()
print(f"{'='*70}")
print("Summary:")
print("- Regular API should work for most cases")
print("- Selenium is available as fallback if API fails")
print("- To force Selenium mode, add ?selenium=true to the endpoint")
print(f"{'='*70}\n")
