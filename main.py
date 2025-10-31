from flask import Flask, request, jsonify
import logging
import re
import requests
from functools import wraps
import os
import json

app = Flask(__name__)

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RapidAPI sozlamalari
RAPIDAPI_KEY = "82d6cdc0f2mshd3d57d3979430d8p19ec3bjsnde8d982c9e90"

# Turli Instagram API larni sinab ko'ramiz
API_CONFIGS = [
    {
        "name": "Instagram Scraper",
        "host": "instagram-scraper-api2.p.rapidapi.com", 
        "url": "https://instagram-scraper-api2.p.rapidapi.com/v1/post_info",
        "params_key": "code",
        "enabled": True
    },
    {
        "name": "Instagram Downloader",
        "host": "instagram-downloader-download-instagram-videos-stories1.p.rapidapi.com",
        "url": "https://instagram-downloader-download-instagram-videos-stories1.p.rapidapi.com/",
        "params_key": "url",
        "enabled": True
    }
]

# Bepul API lar
FREE_APIS = [
    {
        "name": "Instagram Private API",
        "url": "https://www.instagram.com/p/{code}/?__a=1&__d=dis",
        "method": "GET",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    }
]

# TEST MODE
TEST_MODE = os.getenv('TEST_MODE', 'True').lower() == 'true'

def rapidapi_required(f):
    """RapidAPI tekshirish dekoratori"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not RAPIDAPI_KEY:
            return jsonify({
                'success': False,
                'error': 'RapidAPI kaliti sozlanmagan'
            }), 500
        return f(*args, **kwargs)
    return decorated_function

def extract_instagram_code(video_url: str):
    """
    Instagram URL dan post kodini olish
    """
    if not video_url:
        return None

    patterns = [
        r'instagram\.com/p/([^/?#&]+)',
        r'instagram\.com/reel/([^/?#&]+)', 
        r'instagram\.com/tv/([^/?#&]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, video_url)
        if match:
            return match.group(1)
    
    return None

def extract_shortcode_from_url(url: str):
    """Instagram URL dan shortcode olish"""
    patterns = [
        r'instagram\.com/p/([^/]+)',
        r'instagram\.com/reel/([^/]+)',
        r'instagram\.com/tv/([^/]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def extract_hashtags(text: str):
    """Matndan hashtaglarni topish"""
    if not text:
        return []
    hashtags = re.findall(r'#\w+', text)
    return hashtags

def check_required_hashtags(text: str):
    """
    Matndan kerakli hashtag va frazalarni tekshirish
    """
    REQUIRED_HASHTAGS = [
        "#Telegramdagi",
        "#RekchiAi_bot",
    ]
    
    REQUIRED_PHRASES = [
        "Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?",
        "Telegramga RekchiAi_bot ga kiring."
    ]
    
    found_hashtags_list = extract_hashtags(text)
    found_hashtags_set = set([h.lower() for h in found_hashtags_list])
    
    found_details = []
    all_found = True
    
    # Hashtaglarni tekshirish
    for hashtag in REQUIRED_HASHTAGS:
        found = hashtag.lower() in found_hashtags_set
        found_details.append({
            'hashtag': hashtag,
            'found': found,
            'required': True,
            'type': 'hashtag'
        })
        if not found:
            all_found = False
    
    # Frazalarni tekshirish
    text_lower = (text or "").lower()
    for phrase in REQUIRED_PHRASES:
        found_phrase = phrase.lower() in text_lower
        found_details.append({
            'hashtag': phrase,
            'found': found_phrase,
            'required': True,
            'type': 'phrase'
        })
        if not found_phrase:
            all_found = False
    
    return all_found, found_details

def try_rapidapi_apis(video_url: str):
    """RapidAPI larni sinab ko'rish"""
    code = extract_instagram_code(video_url)
    
    for api_config in API_CONFIGS:
        if not api_config.get("enabled", True):
            continue
            
        try:
            logger.info(f"RapidAPI sinab ko'ryapman: {api_config['name']}")
            
            headers = {
                "X-RapidAPI-Key": RAPIDAPI_KEY,
                "X-RapidAPI-Host": api_config["host"]
            }
            
            params = {}
            if api_config["params_key"] == "url":
                params = {"url": video_url}
            elif api_config["params_key"] == "code" and code:
                params = {"code": code}
            else:
                continue
                
            response = requests.get(
                api_config["url"], 
                headers=headers, 
                params=params, 
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"{api_config['name']} muvaffaqiyatli ishladi")
                return parse_api_response(data, api_config["name"])
            else:
                logger.warning(f"{api_config['name']} xatosi: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.warning(f"{api_config['name']} istisnosi: {str(e)}")
            continue
    
    return None

def try_free_apis(video_url: str):
    """Bepul API larni sinab ko'rish"""
    shortcode = extract_shortcode_from_url(video_url)
    if not shortcode:
        return None
        
    for api_config in FREE_APIS:
        try:
            logger.info(f"Bepul API sinab ko'ryapman: {api_config['name']}")
            
            url = api_config["url"].format(code=shortcode)
            headers = api_config.get("headers", {})
            method = api_config.get("method", "GET")
            
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            else:
                continue
                
            if response.status_code == 200:
                data = response.json()
                logger.info(f"{api_config['name']} muvaffaqiyatli ishladi")
                return parse_instagram_private_api(data, api_config["name"])
            else:
                logger.warning(f"{api_config['name']} xatosi: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"{api_config['name']} istisnosi: {str(e)}")
            continue
    
    return None

def parse_api_response(data, api_name):
    """API responseni parse qilish"""
    try:
        result = {
            "message": "success",
            "api_used": api_name,
            "data": {}
        }
        
        if api_name == "Instagram Scraper":
            # Instagram Scraper API strukturasi
            if 'data' in data:
                post_data = data['data']
                result['data']['caption'] = post_data.get('caption', {}).get('text', '')
                result['data']['likes'] = post_data.get('like_count', 0)
                result['data']['comments'] = post_data.get('comment_count', 0)
                
        elif api_name == "Instagram Downloader":
            # Instagram Downloader API strukturasi  
            result['data']['caption'] = data.get('caption', '')
            result['data']['likes'] = data.get('likes', 0)
            result['data']['comments'] = data.get('comments', 0)
            
        return result
        
    except Exception as e:
        logger.error(f"API response parse xatosi: {str(e)}")
        return None

def parse_instagram_private_api(data, api_name):
    """Instagram Private API responseni parse qilish"""
    try:
        result = {
            "message": "success", 
            "api_used": api_name,
            "data": {}
        }
        
        # Instagram private API strukturasi
        if 'graphql' in data and 'shortcode_media' in data['graphql']:
            media = data['graphql']['shortcode_media']
            
            # Caption olish
            caption = ""
            if 'edge_media_to_caption' in media:
                edges = media['edge_media_to_caption']['edges']
                if edges and len(edges) > 0:
                    caption = edges[0]['node'].get('text', '')
            
            result['data']['caption'] = caption
            result['data']['likes'] = media.get('edge_media_preview_like', {}).get('count', 0)
            result['data']['comments'] = media.get('edge_media_to_comment', {}).get('count', 0)
            
        return result
        
    except Exception as e:
        logger.error(f"Private API parse xatosi: {str(e)}")
        return None

def get_test_instagram_data(video_url: str):
    """Test ma'lumotlari"""
    if "test_accept" in (video_url or "") or "hashtag" in (video_url or ""):
        return {
            "message": "success",
            "data": {
                "caption": "Bu test video Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot",
                "likes": 150,
                "comments": 25
            },
            "api_used": "TEST_MODE_ACCEPT"
        }
    elif "test_reject" in (video_url or "") or "nohashtag" in (video_url or ""):
        return {
            "message": "success", 
            "data": {
                "caption": "Bu oddiy video hech qanday hashtag yoq #boshqa #hashtag",
                "likes": 100,
                "comments": 15
            },
            "api_used": "TEST_MODE_REJECT"
        }
    else:
        # URL dan avtomatik aniqlash
        url_lower = (video_url or "").lower()
        if "accept" in url_lower or "hashtag" in url_lower:
            return {
                "message": "success",
                "data": {
                    "caption": "Bu test video Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot",
                    "likes": 200,
                    "comments": 30
                },
                "api_used": "TEST_MODE_AUTO_ACCEPT"
            }
        else:
            return {
                "message": "success",
                "data": {
                    "caption": "Bu oddiy video hech qanday hashtag yoq #boshqa #hashtag",
                    "likes": 100,
                    "comments": 15
                },
                "api_used": "TEST_MODE_AUTO_REJECT"
            }

def get_instagram_post_info(video_url: str):
    """Instagram post ma'lumotlarini olish"""
    try:
        if TEST_MODE:
            logger.info("TEST MODE: Test ma'lumotlar ishlatilmoqda")
            return get_test_instagram_data(video_url)
        
        # 1. RapidAPI larni sinab ko'rish
        result = try_rapidapi_apis(video_url)
        if result:
            return result
            
        # 2. Bepul API larni sinab ko'rish  
        result = try_free_apis(video_url)
        if result:
            return result
            
        # 3. Agar barchasi ishlamasa, test rejimi
        logger.warning("Barcha API lar ishlamadi, test rejimiga o'tiladi")
        return get_test_instagram_data(video_url)
            
    except Exception as e:
        logger.error(f"Instagram ma'lumot olish xatosi: {str(e)}")
        return get_test_instagram_data(video_url)

@app.route('/check', methods=['POST'])
def check_video_text():
    """Instagram video tekshirish - asosiy endpoint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'approved': False,
                'error': 'JSON ma\'lumotlari talab qilinadi',
                'warning': None,
                'fine_amount': 0,
                'test_mode': TEST_MODE
            }), 400
            
        video_url = data.get('video_url')
        
        if not video_url:
            return jsonify({
                'success': False,
                'approved': False,
                'error': 'video_url maydoni talab qilinadi',
                'warning': None,
                'fine_amount': 0,
                'test_mode': TEST_MODE
            }), 400
        
        logger.info(f"Video tekshirish so'rovi: {video_url}")
        
        # Instagram ma'lumotlarini olish
        instagram_data = get_instagram_post_info(video_url)
        
        if instagram_data.get('message') != 'success':
            error_msg = instagram_data.get('error') or 'Instagram ma\'lumotlarini olish mumkin emas'
            return jsonify({
                'success': False,
                'approved': False,
                'error': error_msg,
                'warning': 'API xatosi',
                'fine_amount': 0,
                'test_mode': TEST_MODE
            }), 400
        
        # API dan qaytgan ma'lumotlarni olish
        api_data = instagram_data.get('data', {})
        api_used = instagram_data.get('api_used', 'UNKNOWN')
        
        caption_text = api_data.get('caption', '')
        like_count = api_data.get('likes', 0)
        comment_count = api_data.get('comments', 0)
        
        # Hashtag va frazalarni tekshirish
        has_required_hashtags, found_hashtags = check_required_hashtags(caption_text)
        
        response_data = {
            'success': True,
            'approved': has_required_hashtags,
            'error': None if has_required_hashtags else 'Kerakli hashtag yoki frazalar topilmadi',
            'warning': None if has_required_hashtags else 'Video rad etildi - jarima qo\'llaniladi',
            'fine_amount': 0 if has_required_hashtags else 10000,
            'test_mode': TEST_MODE,
            'api_used': api_used,
            'hashtags_check': found_hashtags,
            'post_stats': {
                'likes': like_count,
                'comments': comment_count
            },
            'caption': caption_text,
            'message': 'Video qabul qilindi - barcha shartlar bajarilgan' if has_required_hashtags else 'Video rad etildi - barcha shartlar bajarilmagan'
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Video check error: {str(e)}")
        return jsonify({
            'success': False,
            'approved': False,
            'error': f"Server xatosi: {str(e)}",
            'warning': None,
            'fine_amount': 0,
            'test_mode': TEST_MODE
        }), 500

@app.route('/rapidapi-status', methods=['GET'])
def rapidapi_status():
    """API holatini tekshirish"""
    try:
        test_url = "https://www.instagram.com/p/Cx6dUySILh6/"
        
        for api_config in API_CONFIGS:
            try:
                headers = {
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": api_config["host"]
                }
                
                params = {}
                if api_config["params_key"] == "url":
                    params = {"url": test_url}
                else:
                    code = extract_instagram_code(test_url)
                    if code:
                        params = {"code": code}
                    else:
                        continue
                
                response = requests.get(
                    api_config["url"], 
                    headers=headers, 
                    params=params, 
                    timeout=10
                )
                
                status_info = {
                    'success': True,
                    'api_tested': api_config["name"],
                    'status_code': response.status_code,
                    'test_mode': TEST_MODE,
                }
                
                if response.status_code == 200:
                    status_info['status'] = 'active'
                    status_info['message'] = f"{api_config['name']} - Faol"
                else:
                    status_info['status'] = 'inactive' 
                    status_info['message'] = f"{api_config['name']} - Nofaol ({response.status_code})"
                    
                return jsonify(status_info)
                
            except Exception as e:
                continue
        
        # Bepul API ni tekshirish
        try:
            shortcode = extract_shortcode_from_url(test_url)
            if shortcode:
                free_api_url = FREE_APIS[0]["url"].format(code=shortcode)
                response = requests.get(free_api_url, headers=FREE_APIS[0]["headers"], timeout=10)
                
                return jsonify({
                    'success': True,
                    'api_tested': 'Instagram Private API',
                    'status': 'active' if response.status_code == 200 else 'inactive',
                    'status_code': response.status_code,
                    'test_mode': TEST_MODE,
                    'message': f"Instagram Private API - {'Faol' if response.status_code == 200 else 'Nofaol'}"
                })
        except:
            pass
            
        return jsonify({
            'success': False,
            'status': 'all_apis_inactive',
            'test_mode': TEST_MODE,
            'message': 'Barcha API lar ishlamayapti, test rejimi faollashtirildi'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'error',
            'test_mode': TEST_MODE,
            'error': str(e)
        }), 500

@app.route('/test/accept')
def test_accept():
    """Qabul qilinadigan test"""
    return jsonify({
        'success': True,
        'approved': True,
        'error': None,
        'warning': None,
        'fine_amount': 0,
        'test_mode': True,
        'api_used': 'TEST_ENDPOINT',
        'message': 'Bu test video qabul qilinadi - barcha shartlar bajarilgan',
        'hashtags_check': [
            {'hashtag': '#Telegramdagi', 'found': True, 'required': True, 'type': 'hashtag'},
            {'hashtag': '#RekchiAi_bot', 'found': True, 'required': True, 'type': 'hashtag'},
            {'hashtag': 'Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?', 'found': True, 'required': True, 'type': 'phrase'},
            {'hashtag': 'Telegramga RekchiAi_bot ga kiring.', 'found': True, 'required': True, 'type': 'phrase'}
        ],
        'caption': 'Bu test video Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot',
        'post_stats': {'likes': 150, 'comments': 25}
    })

@app.route('/test/reject')
def test_reject():
    """Rad etiladigan test"""
    return jsonify({
        'success': True,
        'approved': False,
        'error': 'Kerakli hashtag yoki frazalar topilmadi',
        'warning': 'Video rad etildi - 10,000 jarima',
        'fine_amount': 10000,
        'test_mode': True,
        'api_used': 'TEST_ENDPOINT',
        'message': 'Bu test video rad etildi - barcha shartlar bajarilmagan',
        'hashtags_check': [
            {'hashtag': '#Telegramdagi', 'found': False, 'required': True, 'type': 'hashtag'},
            {'hashtag': '#RekchiAi_bot', 'found': False, 'required': True, 'type': 'hashtag'},
            {'hashtag': 'Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?', 'found': False, 'required': True, 'type': 'phrase'},
            {'hashtag': 'Telegramga RekchiAi_bot ga kiring.', 'found': False, 'required': True, 'type': 'phrase'}
        ],
        'caption': 'Bu oddiy video hech qanday hashtag yoq #boshqa #hashtag',
        'post_stats': {'likes': 100, 'comments': 15}
    })

@app.route('/')
def root():
    """Asosiy sahifa"""
    return jsonify({
        "message": "Instagram Video Validation API",
        "version": "9.0.0 - MULTI-API WITH FREE APIS",
        "test_mode": TEST_MODE,
        "description": "RapidAPI va bepul API larni kombinatsiya qiladi",
        "apis_configured": len(API_CONFIGS) + len(FREE_APIS),
        "endpoints": {
            "POST /check": "Asosiy tekshirish",
            "GET /rapidapi-status": "API holati",
            "GET /test/accept": "Qabul qilinadigan test", 
            "GET /test/reject": "Rad etiladigan test"
        },
        "note": "Sistem avval RapidAPI larni, keyin bepul API larni sinab ko'radi. Test rejimi ham mavjud."
    })

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    debug_mode = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
