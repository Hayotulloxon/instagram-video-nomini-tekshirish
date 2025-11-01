from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import logging
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import json
from datetime import datetime
import os

app = Flask(__name__)

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global sozlamalar
MAX_RETRIES = 3
REQUEST_TIMEOUT = 15

class InstagramChecker:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
        ]
    
    def get_random_user_agent(self):
        import random
        return random.choice(self.user_agents)
    
    def extract_shortcode(self, url):
        """Instagram URL dan shortcode olish"""
        patterns = [
            r'instagram\.com/p/([^/?]+)',
            r'instagram\.com/reel/([^/?]+)',
            r'instagram\.com/tv/([^/?]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def check_required_content(self, text):
        """Matndan kerakli hashtag va frazalarni tekshirish"""
        REQUIRED_HASHTAGS = [
            "#Telegramdagi",
            "#RekchiAi_bot",
        ]
        
        REQUIRED_PHRASES = [
            "Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?",
            "Telegramga RekchiAi_bot ga kiring."
        ]
        
        if not text:
            return False, []
        
        # Hashtaglarni tekshirish
        found_hashtags = re.findall(r'#\w+', text)
        found_hashtags_set = set([h.lower() for h in found_hashtags])
        
        found_details = []
        all_found = True
        
        # Hashtaglarni tekshirish
        for hashtag in REQUIRED_HASHTAGS:
            required_lower = hashtag.lower()
            found = required_lower in found_hashtags_set
            
            found_details.append({
                'hashtag': hashtag,
                'found': found,
                'required': True,
                'type': 'hashtag'
            })
            if not found:
                all_found = False
        
        # Frazalarni tekshirish
        text_lower = text.lower()
        
        for phrase in REQUIRED_PHRASES:
            phrase_lower = phrase.lower()
            found_phrase = phrase_lower in text_lower
            
            found_details.append({
                'hashtag': phrase,
                'found': found_phrase,
                'required': True,
                'type': 'phrase'
            })
            if not found_phrase:
                all_found = False
        
        return all_found, found_details
    
    def check_with_requests(self, video_url):
        """Requests va BeautifulSoup bilan tekshirish"""
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        try:
            response = requests.get(video_url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # JSON ma'lumotlarini extract qilish
            script_tags = soup.find_all('script', type='text/javascript')
            caption = ""
            
            for script in script_tags:
                if script.string:
                    script_content = script.string
                    # Turli JSON patternlarini sinab ko'rish
                    patterns = [
                        r'"caption":"([^"]*)"',
                        r'"edge_media_to_caption":{"edges":\[\{"node":{"text":"([^"]*)"',
                        r'"text":"([^"]*)"',
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, script_content)
                        for match in matches:
                            if match and len(match) > 10:  # Qisqa matnlarni filter qilish
                                caption = match
                                # Unicode escape sequence larni decode qilish
                                try:
                                    caption = caption.encode('latin-1').decode('unicode_escape')
                                except:
                                    pass
                                break
                    if caption:
                        break
            
            # Agar JSON topilmasa, meta taglardan olish
            if not caption:
                meta_description = soup.find('meta', property='og:description')
                if meta_description:
                    caption = meta_description.get('content', '')
            
            # Agar hali ham caption topilmasa, title dan olish
            if not caption:
                title_tag = soup.find('title')
                if title_tag:
                    caption = title_tag.get_text()
            
            # Tekshirish
            approved, found_details = self.check_required_content(caption)
            
            return {
                'success': True,
                'approved': approved,
                'caption': caption,
                'found_details': found_details,
                'method': 'requests'
            }
            
        except Exception as e:
            logger.error(f"Requests method error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'method': 'requests'
            }
    
    def check_with_selenium(self, video_url):
        """Selenium bilan tekshirish"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"--user-agent={self.get_random_user_agent()}")
        
        driver = None
        try:
            # WebDriverManager bilan Chrome driver ni o'rnatish
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            driver.get(video_url)
            
            # Kutish va dynamic content load bo'lishini kutish
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            time.sleep(3)  # Additional wait for dynamic content
            
            # Caption ni topish uchun turli selectorlar
            caption_selectors = [
                "h1._aacl._aaco._aacu._aacx._aad7._aade",
                "div._a9zs",
                "span._aacl._aaco._aacu._aacx._aad7._aade",
                "article ._a9zr",
                "section ._a9zr",
                "div._a9zr",
                "[data-testid='post-comment-root']",
            ]
            
            caption = ""
            for selector in caption_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) > 10:  # Faqat mazmunli matnlarni olish
                            caption = text
                            break
                    if caption:
                        break
                except:
                    continue
            
            # Agar hali caption topilmasa, butun page text ni olish
            if not caption:
                caption = driver.find_element(By.TAG_NAME, "body").text
            
            # Tekshirish
            approved, found_details = self.check_required_content(caption)
            
            return {
                'success': True,
                'approved': approved,
                'caption': caption,
                'found_details': found_details,
                'method': 'selenium'
            }
            
        except Exception as e:
            logger.error(f"Selenium method error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'method': 'selenium'
            }
        finally:
            if driver:
                driver.quit()
    
    def check_instagram_post(self, video_url):
        """Asosiy tekshirish funksiyasi - barcha usullarni sinab ko'radi"""
        
        # Avval requests method ni sinab ko'rish
        result = self.check_with_requests(video_url)
        if result['success']:
            return result
        
        # Agar requests ishlamasa, selenium ni sinab ko'rish
        logger.info("Requests method ishlamadi, Selenium ni sinab ko'ryapman...")
        result = self.check_with_selenium(video_url)
        if result['success']:
            return result
        
        # Agar ikkala usul ham ishlamasa
        return {
            'success': False,
            'approved': False,
            'error': 'Barcha tekshirish usullari ishlamadi',
            'method': 'all_failed'
        }

# Global InstagramChecker instance
instagram_checker = InstagramChecker()

@app.route('/check', methods=['POST', 'GET'])
def check_video():
    """Asosiy tekshirish endpoint - PHP bot bilan mos keladi"""
    try:
        # JSON data ni olish
        if request.method == 'POST':
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()
        else:
            data = request.args.to_dict()
        
        video_url = data.get('video_url') or data.get('url')
        
        if not video_url:
            return jsonify({
                'success': False,
                'approved': False,
                'error': 'video_url maydoni talab qilinadi',
                'has_text': False,
                'title': None
            }), 400
        
        logger.info(f"Video tekshirish so'rovi: {video_url}")
        
        # Instagram post ni tekshirish
        result = instagram_checker.check_instagram_post(video_url)
        
        if not result['success']:
            return jsonify({
                'success': False,
                'approved': False,
                'error': result.get('error', 'Tekshirish amalga oshirilmadi'),
                'has_text': False,
                'title': None
            }), 400
        
        # PHP bot uchun mos response
        response_data = {
            'success': True,
            'approved': result['approved'],
            'has_text': result['approved'],  # PHP bot uchun
            'error': None,
            'title': result.get('caption', '')[:100] + '...' if result.get('caption') else 'Instagram video',
            'method_used': result.get('method', 'unknown'),
            'caption_preview': result.get('caption', '')[:200] if result.get('caption') else '',
            'found_details': result.get('found_details', []),
            'message': 'Video qabul qilindi' if result['approved'] else 'Video rad etildi - kerakli matnlar topilmadi'
        }
        
        logger.info(f"Tekshirish natijasi: {'Qabul qilindi' if result['approved'] else 'Rad etildi'} - Method: {result.get('method')}")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Umumiy xato: {str(e)}")
        return jsonify({
            'success': False,
            'approved': False,
            'error': f"Server xatosi: {str(e)}",
            'has_text': False,
            'title': None
        }), 500

@app.route('/status', methods=['GET'])
def status():
    """Server holatini tekshirish"""
    return jsonify({
        'status': 'online',
        'service': 'Instagram Video Checker',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0'
    })

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint - PHP bot sinash uchun"""
    test_url = request.args.get('url', '')
    
    if 'test_accept' in test_url:
        return jsonify({
            'success': True,
            'approved': True,
            'has_text': True,
            'title': 'Test video - Qabul qilindi',
            'method_used': 'test',
            'message': 'TEST: Video qabul qilindi'
        })
    elif 'test_reject' in test_url:
        return jsonify({
            'success': True,
            'approved': False,
            'has_text': False,
            'title': 'Test video - Rad etildi',
            'method_used': 'test',
            'message': 'TEST: Video rad etildi'
        })
    else:
        return jsonify({
            'success': True,
            'approved': True,
            'has_text': True,
            'title': 'Standart test video',
            'method_used': 'test',
            'message': 'TEST: Standart video qabul qilindi'
        })

@app.route('/')
def home():
    """Bosh sahifa"""
    return jsonify({
        'service': 'Instagram Video Validation API',
        'version': '1.0',
        'endpoints': {
            'POST /check': 'Video tekshirish',
            'GET /status': 'Server holati',
            'GET /test': 'Test endpoint'
        },
        'usage': 'POST /check with {"video_url": "instagram_url"}'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)
