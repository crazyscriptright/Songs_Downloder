"""
JioSaavn Selenium-based Suggestions Scraper
Uses real browser automation to get recommendations
"""

import time
import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class JioSaavnSeleniumScraper:
    def __init__(self, headless=True):
        self.driver = None
        self.headless = headless
    
    def init_driver(self):
        """Initialize Selenium WebDriver"""
        if self.driver:
            return
        
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        # Performance optimizations
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-popup-blocking')
        
        # Set user agent
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
        
        # Indian locale
        chrome_options.add_argument('--lang=en-IN')
        chrome_options.add_experimental_option('prefs', {
            'intl.accept_languages': 'en-IN,en-US,en',
            'profile.default_content_setting_values.notifications': 2,
            'profile.default_content_settings.popups': 0
        })
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            print("✅ Selenium WebDriver initialized")
        except Exception as e:
            print(f"❌ Failed to initialize WebDriver: {e}")
            raise
    
    def close_driver(self):
        """Close WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                print("🔒 WebDriver closed")
            except:
                pass
            self.driver = None
    
    def get_suggestions_by_pid(self, pid, language='english', max_results=10):
        """
        Get JioSaavn suggestions using Selenium by navigating to song page
        
        Args:
            pid: Song PID (perma_url ID)
            language: Language preference (default: english)
            max_results: Maximum number of suggestions to return
            
        Returns:
            List of song suggestions
        """
        suggestions = []
        
        try:
            self.init_driver()
            
            # Build song URL from PID
            # JioSaavn URLs format: https://www.jiosaavn.com/song/{song-name}/{pid}
            url = f"https://www.jiosaavn.com/song/_/{pid}"
            
            print(f"🌐 Navigating to: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Method 1: Make API call with cookies from browser (most reliable)
            try:
                print("🔄 Method 1: API with browser cookies")
                cookies = self.driver.get_cookies()
                
                # Build API URL
                api_url = f"https://www.jiosaavn.com/api.php?__call=reco.getreco&api_version=4&_format=json&_marker=0&ctx=wap6dot0&pid={pid}&language={language}"
                
                import requests
                session = requests.Session()
                
                # Add cookies from browser
                for cookie in cookies:
                    session.cookies.set(cookie['name'], cookie['value'])
                
                # Add headers from browser
                headers = {
                    'User-Agent': self.driver.execute_script('return navigator.userAgent;'),
                    'Referer': url,
                    'Accept': 'application/json',
                    'Accept-Language': 'en-IN,en-US;q=0.9,en;q=0.8',
                }
                
                response = session.get(api_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if isinstance(data, list):
                        for item in data[:max_results]:
                            parsed = self._parse_song_item(item)
                            if parsed:
                                suggestions.append(parsed)
                    
                    if suggestions:
                        print(f"✅ Got {len(suggestions)} suggestions from API with browser cookies")
                        return suggestions
                
            except Exception as e:
                print(f"⚠️ Method 1 failed: {e}")
            
            # Method 2: Extract from page JSON data
            try:
                print("🔄 Method 2: Extract from page JSON")
                # JioSaavn embeds JSON data in script tags
                scripts = self.driver.find_elements(By.TAG_NAME, 'script')
                
                for script in scripts:
                    script_content = script.get_attribute('innerHTML')
                    
                    if not script_content:
                        continue
                    
                    # Look for recommendations data
                    if 'recommendations' in script_content or 'similar' in script_content.lower():
                        # Try to extract JSON
                        json_match = re.search(r'\{.*"recommendations".*\}', script_content, re.DOTALL)
                        if json_match:
                            try:
                                data = json.loads(json_match.group(0))
                                if 'recommendations' in data:
                                    reco_data = data['recommendations']
                                    if isinstance(reco_data, list):
                                        for item in reco_data[:max_results]:
                                            parsed = self._parse_song_item(item)
                                            if parsed:
                                                suggestions.append(parsed)
                                    if suggestions:
                                        print(f"✅ Extracted {len(suggestions)} suggestions from JSON")
                                        return suggestions
                            except json.JSONDecodeError:
                                pass
                
            except Exception as e:
                print(f"⚠️ Method 2 failed: {e}")
            
            # Method 3: Scrape song cards from DOM (last resort)
            try:
                print("🔄 Method 3: Scrape from DOM")
                # Find all song cards/items on the page
                song_selectors = [
                    '//a[contains(@href, "/song/")]',
                    '//li[@class="c-list__item"]',
                    '//div[contains(@class, "o-flag__body")]',
                ]
                
                for selector in song_selectors:
                    try:
                        song_elements = self.driver.find_elements(By.XPATH, selector)
                        
                        if song_elements:
                            print(f"✅ Found {len(song_elements)} song elements using: {selector}")
                            
                            for element in song_elements[:max_results * 2]:  # Get more to filter
                                try:
                                    song_data = self._extract_song_from_element(element)
                                    if song_data and song_data not in suggestions:
                                        suggestions.append(song_data)
                                        if len(suggestions) >= max_results:
                                            break
                                except Exception:
                                    continue
                            
                            if suggestions:
                                print(f"✅ Scraped {len(suggestions)} suggestions from DOM")
                                return suggestions
                    except:
                        continue
                
            except Exception as e:
                print(f"⚠️ Method 3 failed: {e}")
            
        except Exception as e:
            print(f"❌ Selenium scraping error: {e}")
        
        finally:
            self.close_driver()
        
        return suggestions
    
    def _parse_song_item(self, item):
        """Parse song item from JSON data"""
        try:
            if not isinstance(item, dict):
                return None
            
            # Extract artist from subtitle
            subtitle = item.get('subtitle', '')
            artist = subtitle.split(' - ')[0] if ' - ' in subtitle else 'Unknown Artist'
            
            return {
                'id': item.get('id', ''),
                'title': item.get('title', ''),
                'artist': artist,
                'subtitle': subtitle,
                'thumbnail': item.get('image', ''),
                'url': item.get('perma_url', ''),
                'duration': str(item.get('duration', 0)) if item.get('duration') else '0:00',
                'language': item.get('language', ''),
                'type': item.get('type', 'song'),
                'year': item.get('year', ''),
                'play_count': item.get('play_count', 0)
            }
        except:
            return None
    
    def _extract_song_from_element(self, element):
        """Extract song data from DOM element"""
        try:
            song_data = {}
            
            # Try to find link
            try:
                link = element.find_element(By.TAG_NAME, 'a')
                song_data['url'] = link.get_attribute('href')
                
                # Extract PID from URL
                if '/song/' in song_data['url']:
                    pid_match = re.search(r'/song/[^/]+/([^/]+)', song_data['url'])
                    if pid_match:
                        song_data['id'] = pid_match.group(1)
            except:
                pass
            
            # Try to find title
            try:
                title_elem = element.find_element(By.XPATH, './/h2 | .//h3 | .//span[@class="c-title"]')
                song_data['title'] = title_elem.text.strip()
            except:
                pass
            
            # Try to find artist/subtitle
            try:
                artist_elem = element.find_element(By.XPATH, './/p | .//span[contains(@class, "c-subtitle")]')
                song_data['subtitle'] = artist_elem.text.strip()
                song_data['artist'] = artist_elem.text.split(' - ')[0] if ' - ' in artist_elem.text else artist_elem.text
            except:
                song_data['artist'] = 'Unknown Artist'
            
            # Try to find thumbnail
            try:
                img = element.find_element(By.TAG_NAME, 'img')
                song_data['thumbnail'] = img.get_attribute('src')
            except:
                pass
            
            # Return only if we have at least title and URL
            if 'title' in song_data and 'url' in song_data:
                return song_data
            
        except:
            pass
        
        return None


# Singleton instance
_scraper_instance = None

def get_jiosaavn_suggestions_selenium(pid, language='english', max_results=10, headless=True):
    """
    Get JioSaavn suggestions using Selenium
    
    Args:
        pid: Song PID
        language: Language preference
        max_results: Maximum results
        headless: Run browser in headless mode
        
    Returns:
        List of suggestions
    """
    global _scraper_instance
    
    # Create scraper instance
    scraper = JioSaavnSeleniumScraper(headless=headless)
    
    try:
        return scraper.get_suggestions_by_pid(pid, language, max_results)
    finally:
        scraper.close_driver()


if __name__ == "__main__":
    # Test
    test_pid = "IgwLcB06"  # Example PID
    print(f"\n🧪 Testing JioSaavn Selenium Scraper")
    print(f"{'='*70}\n")
    
    suggestions = get_jiosaavn_suggestions_selenium(test_pid, headless=True)
    
    print(f"\n✅ Found {len(suggestions)} suggestions:")
    for i, song in enumerate(suggestions, 1):
        print(f"{i}. {song.get('title', 'N/A')} - {song.get('artist', 'N/A')}")
