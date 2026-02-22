"""
Simplified JioSaavn Suggestions Scraper
2 Methods: API (with India geo-location) → Selenium fallback
"""

import requests
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

class JioSaavnSuggestions:
    def __init__(self):
        self.driver = None
        # India-based headers (same as search)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://www.jiosaavn.com",
            "Referer": "https://www.jiosaavn.com/",
            "X-Requested-With": "XMLHttpRequest",
            "X-Forwarded-For": "103.21.124.0",  # Indian IP range
            "CF-IPCountry": "IN"  # Cloudflare country header for India
        }
    
    def get_suggestions(self, pid, language='hindi', max_results=16):
        """Get song suggestions - API first, then Selenium fallback"""
        
        print(f"\n{'='*60}")
        print(f"🎵 Getting suggestions for PID: {pid} (Language: {language})")
        print(f"{'='*60}\n")
        
        suggestions = []
        
        # METHOD 1: Direct API with India geo-location headers
        print("🔄 Method 1: API with India geo-location headers")
        suggestions = self._try_api(pid, language, max_results)
        
        if suggestions:
            print(f"✅ API Success: Got {len(suggestions)} suggestions")
            return suggestions
        
        # METHOD 2: Selenium fallback (scrape from page)
        print("\n⚠️ API returned empty, trying Selenium fallback...")
        print("🔄 Method 2: Selenium web scraping")
        suggestions = self._try_selenium(pid, language, max_results)
        
        if suggestions:
            print(f"✅ Selenium Success: Got {len(suggestions)} suggestions")
        else:
            print(f"❌ No suggestions found from any method")
        
        return suggestions
    
    def _try_api(self, pid, language, max_results):
        """Method 1: Try API with India headers"""
        suggestions = []
        
        try:
            api_url = f"https://www.jiosaavn.com/api.php?__call=reco.getreco&api_version=4&_format=json&_marker=0&ctx=wap6dot0&pid={pid}&language={language}"
            
            print(f"   📡 API URL: {api_url}")
            print(f"   🌍 Using India geo-location: X-Forwarded-For: 103.21.124.0, CF-IPCountry: IN")
            
            response = requests.get(api_url, headers=self.headers, timeout=10)
            
            print(f"   📊 Status: {response.status_code}, Size: {len(response.content)} bytes")
            
            if response.status_code == 200 and len(response.content) > 10:
                data = response.json()
                
                if isinstance(data, list) and len(data) > 0:
                    print(f"   ✅ API returned {len(data)} items")
                    
                    for item in data[:max_results]:
                        song_data = self._parse_song_item(item)
                        if song_data:
                            suggestions.append(song_data)
                else:
                    print(f"   ⚠️ API returned empty list or invalid data")
            else:
                print(f"   ⚠️ API call failed or returned minimal data")
        
        except Exception as e:
            print(f"   ❌ API Error: {e}")
        
        return suggestions
    
    def _try_selenium(self, pid, language, max_results):
        """Method 2: Selenium scraping"""
        suggestions = []
        
        try:
            # Initialize driver
            self._init_driver()
            
            # Navigate to song page
            url = f"https://www.jiosaavn.com/song/_/{pid}"
            print(f"   🌐 Loading: {url}")
            
            self.driver.get(url)
            time.sleep(5)  # Wait for page load
            
            page_title = self.driver.title
            page_size = len(self.driver.page_source)
            print(f"   📄 Page loaded: {page_title[:50]}")
            print(f"   📄 Page size: {page_size} chars")
            
            if "404" in page_title.lower():
                print(f"   ❌ Page not found")
                return suggestions
            
            # Try to find song links on the page
            print(f"   🔍 Searching for song links...")
            
            # Multiple selectors to find recommendation links
            selectors = [
                '//a[contains(@href, "/song/") and not(contains(@href, "/' + pid + '"))]',
                '//div[contains(@class, "song")]//a[contains(@href, "/song/")]',
                '//li//a[contains(@href, "/song/")]',
            ]
            
            found_links = set()
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        print(f"   ✅ Found {len(elements)} links with selector: {selector}")
                        
                        for elem in elements[:max_results * 2]:
                            try:
                                href = elem.get_attribute('href')
                                if href and '/song/' in href and href not in found_links:
                                    found_links.add(href)
                                    
                                    # Extract song ID
                                    import re
                                    song_id_match = re.search(r'/song/[^/]+/([^/\?]+)', href)
                                    if song_id_match:
                                        song_id = song_id_match.group(1)
                                        
                                        # Get title
                                        title = elem.text.strip() or elem.get_attribute('title') or 'Unknown'
                                        
                                        # Try to find thumbnail
                                        thumbnail = ''
                                        try:
                                            parent = elem.find_element(By.XPATH, './ancestor::*[1]')
                                            img = parent.find_element(By.TAG_NAME, 'img')
                                            thumbnail = img.get_attribute('src') or img.get_attribute('data-src') or ''
                                        except:
                                            pass
                                        
                                        song_data = {
                                            'id': song_id,
                                            'title': title,
                                            'artist': 'Unknown Artist',
                                            'subtitle': '',
                                            'thumbnail': thumbnail,
                                            'url': href,
                                            'duration': '0:00',
                                            'language': language,
                                            'type': 'song',
                                            'year': '',
                                            'play_count': 0
                                        }
                                        
                                        suggestions.append(song_data)
                                        
                                        if len(suggestions) >= max_results:
                                            break
                            except:
                                continue
                        
                        if len(suggestions) >= max_results:
                            break
                except:
                    continue
            
            print(f"   📊 Found {len(found_links)} unique song links")
            print(f"   📊 Extracted {len(suggestions)} complete song data")
        
        except Exception as e:
            print(f"   ❌ Selenium Error: {e}")
        
        finally:
            self._close_driver()
        
        return suggestions
    
    def _init_driver(self):
        """Initialize Chrome WebDriver"""
        if self.driver:
            return
        
        print("   🚀 Initializing Chrome WebDriver...")
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        print("   ✅ WebDriver initialized")
    
    def _close_driver(self):
        """Close WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                print("   🔒 WebDriver closed")
            except:
                pass
            self.driver = None
    
    def _parse_song_item(self, item):
        """Parse song item from API response"""
        try:
            if not isinstance(item, dict):
                return None
            
            # Extract song data
            song_id = item.get('id', '') or item.get('perma_url', '').split('/')[-1]
            title = item.get('title', '') or item.get('song', '')
            
            if not song_id or not title:
                return None
            
            return {
                'id': str(song_id),
                'title': title,
                'artist': item.get('primary_artists', '') or item.get('music', '') or 'Unknown Artist',
                'subtitle': item.get('subtitle', ''),
                'thumbnail': item.get('image', '') or item.get('header_desc', ''),
                'url': item.get('perma_url', ''),
                'duration': item.get('duration', '') or item.get('more_info', {}).get('duration', '0:00'),
                'language': item.get('language', ''),
                'type': 'song',
                'year': str(item.get('year', '')),
                'play_count': int(item.get('play_count', 0))
            }
        
        except Exception as e:
            print(f"   ⚠️ Parse error: {e}")
            return None


# Test function
def test_suggestions(pid, language='hindi'):
    """Test suggestions locally"""
    scraper = JioSaavnSuggestions()
    results = scraper.get_suggestions(pid, language, max_results=10)
    
    print(f"\n{'='*60}")
    print(f"📊 FINAL RESULTS")
    print(f"{'='*60}")
    print(f"Total suggestions: {len(results)}\n")
    
    if results:
        for i, song in enumerate(results, 1):
            print(f"{i}. {song['title']}")
            print(f"   Artist: {song['artist']}")
            print(f"   ID: {song['id']}")
            print(f"   URL: {song.get('url', 'N/A')}")
            print()
    else:
        print("❌ No results found")
    
    return results


if __name__ == '__main__':
    # Test with the PID that was failing on Heroku
    test_pid = '9JnbejLw'
    print("Testing JioSaavn Suggestions Locally")
    print("=" * 60)
    test_suggestions(test_pid, 'hindi')
