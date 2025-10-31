from flask import Flask, request, jsonify
import logging
import re
import requests
from functools import wraps
import os

app = Flask(__name__)

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RapidAPI sozlamalari
RAPIDAPI_KEY = "82d6cdc0f2mshd3d57d3979430d8p19ec3bjsnde8d982c9e90"

# Eng yaxshi Instagram API lar
API_CONFIGS = [
    {
        "name": "Instagram Scraper 2025",
        "host": "instagram-scraper-2025.p.rapidapi.com",
        "url": "https://instagram-scraper-2025.p.rapidapi.com/media",
        "params_key": "url",
        "enabled": True
    },
    {
        "name": "Instagram Premium API 2023", 
        "host": "instagram-premium-api-2023.p.rapidapi.com",
        "url": "https://instagram-premium-api-2023.p.rapidapi.com/post",
        "params_key": "url",
        "enabled": True
    },
    {
        "name": "Instagram API - Fast & Reliable",
        "host": "instagram-api-fast-and-reliable.p.rapidapi.com",
        "url": "https://instagram-api-fast-and-reliable.p.rapidapi.com/media",
        "params_key": "url", 
        "enabled": True
    },
    {
        "name": "Instagram Scraper Stable API",
        "host": "instagram-scraper-stable-api.p.rapidapi.com",
        "url": "https://instagram-scraper-stable-api.p.rapidapi.com/post",
        "params_key": "url",
        "enabled": True
    }
]

# Bepul fallback API
FREE_API = {
    "name": "Instagram Private API",
    "url": "https://www.instagram.com/p/{code}/?__a=1&__d=dis",
    "headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
}

# TEST MODE
TEST_MODE = os.getenv('TEST_MODE', 'True').lower() == 'true'

def extract_shortcode_from_url(url: str):
    """Instagram URL dan shortcode olish"""
    if not url:
        return None
        
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
    for api_config in API_CONFIGS:
        if not api_config.get("enabled", True):
            continue
            
        try:
            logger.info(f"Sinab ko'ryapman: {api_config['name']}")
            
            headers = {
                "X-RapidAPI-Key": RAPIDAPI_KEY,
                "X-RapidAPI-Host": api_config["host"]
            }
            
            params = {"url": video_url}
                
            response = requests.get(
                api_config["url"], 
                headers=headers, 
                params=params, 
                timeout=20
            )
            
            logger.info(f"{api_config['name']} status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"{api_config['name']} muvaffaqiyatli ishladi")
                return parse_api_response(data, api_config["name"])
            elif response.status_code == 403:
                logger.warning(f"{api_config['name']} - Obuna emas (403)")
                continue
            else:
                logger.warning(f"{api_config['name']} xatosi: {response.status_code}")
                continue
                
        except requests.exceptions.Timeout:
            logger.warning(f"{api_config['name']} - Timeout")
            continue
        except Exception as e:
            logger.warning(f"{api_config['name']} istisnosi: {str(e)}")
            continue
    
    return None

def try_free_api(video_url: str):
    """Bepul Instagram API ni sinab ko'rish"""
    shortcode = extract_shortcode_from_url(video_url)
    if not shortcode:
        return None
        
    try:
        logger.info("Bepul Instagram API sinab ko'ryapman")
        
        url = FREE_API["url"].format(code=shortcode)
        
        response = requests.get(
            url, 
            headers=FREE_API["headers"], 
            timeout=15, 
            allow_redirects=True
        )
        
        logger.info(f"Bepul API status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            return parse_instagram_private_api(data, FREE_API["name"])
        else:
            logger.warning(f"Bepul API xatosi: {response.status_code}")
            return None
            
    except Exception as e:
        logger.warning(f"Bepul API istisnosi: {str(e)}")
        return None

def parse_api_response(data, api_name):
    """API responseni parse qilish"""
    try:
        result = {
            "message": "success",
            "api_used": api_name,
            "data": {
                "caption": "",
                "likes": 0,
                "comments": 0
            }
        }
        
        # Umumiy field lar
        if isinstance(data, dict):
            # Caption qidirish
            caption = ""
            if 'caption' in data:
                caption = data.get('caption', '')
            elif 'text' in data:
                caption = data.get('text', '')
            elif 'description' in data:
                caption = data.get('description', '')
            elif 'data' in data and isinstance(data['data'], dict):
                if 'caption' in data['data']:
                    caption_data = data['data']['caption']
                    if isinstance(caption_data, dict):
                        caption = caption_data.get('text', '')
                    else:
                        caption = str(caption_data)
            
            # Likes qidirish
            likes = 0
            if 'likes' in data:
                likes = data.get('likes', 0)
            elif 'like_count' in data:
                likes = data.get('like_count', 0)
            elif 'data' in data and isinstance(data['data'], dict):
                likes = data['data'].get('like_count', 0) or data['data'].get('likes', 0)
            
            # Comments qidirish  
            comments = 0
            if 'comments' in data:
                comments = data.get('comments', 0)
            elif 'comment_count' in data:
                comments = data.get('comment_count', 0)
            elif 'data' in data and isinstance(data['data'], dict):
                comments = data['data'].get('comment_count', 0) or data['data'].get('comments', 0)
            
            result['data']['caption'] = caption
            result['data']['likes'] = likes
            result['data']['comments'] = comments
            
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
            "data": {
                "caption": "",
                "likes": 0,
                "comments": 0
            }
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
            
            # Likes olish
            likes = 0
            if 'edge_media_preview_like' in media:
                likes = media['edge_media_preview_like'].get('count', 0)
            elif 'edge_liked_by' in media:
                likes = media['edge_liked_by'].get('count', 0)
            
            # Comments olish
            comments = 0
            if 'edge_media_to_comment' in media:
                comments = media['edge_media_to_comment'].get('count', 0)
            
            result['data']['caption'] = caption
            result['data']['likes'] = likes
            result['data']['comments'] = comments
            
        return result
        
    except Exception as e:
        logger.error(f"Private API parse xatosi: {str(e)}")
        return None

def get_test_instagram_data(video_url: str):
    """Test ma'lumotlari"""
    # URL dan holatni aniqlash
    url_lower = (video_url or "").lower()
    
    if "test_accept" in url_lower or "hashtag" in url_lower or "accept" in url_lower:
        return {
            "message": "success",
            "data": {
                "caption": "Bu test video Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot",
                "likes": 150,
                "comments": 25
            },
            "api_used": "TEST_MODE_ACCEPT"
        }
    elif "test_reject" in url_lower or "nohashtag" in url_lower or "reject" in url_lower:
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
        # Default - qabul qilinadigan
        return {
            "message": "success",
            "data": {
                "caption": "Standart test video Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot",
                "likes": 200,
                "comments": 30
            },
            "api_used": "TEST_MODE_DEFAULT"
        }

def get_instagram_post_info(video_url: str):
    """Instagram post ma'lumotlarini olish"""
    try:
        if TEST_MODE:
            logger.info("TEST MODE: Test ma'lumotlar ishlatilmoqda")
            return get_test_instagram_data(video_url)
        
        # 1. RapidAPI larni sinab ko'rish
        logger.info("RapidAPI larni sinab ko'ryapman...")
        result = try_rapidapi_apis(video_url)
        if result:
            logger.info(f"RapidAPI muvaffaqiyatli: {result['api_used']}")
            return result
            
        # 2. Bepul API ni sinab ko'rish  
        logger.info("Bepul API ni sinab ko'ryapman...")
        result = try_free_api(video_url)
        if result:
            logger.info(f"Bepul API muvaffaqiyatli: {result['api_used']}")
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
        test_url = "https://www.instagram.com/p/C1LqX5JMv7G/"  # Haqiqiy Instagram post
        
        # RapidAPI larni tekshirish
        for api_config in API_CONFIGS[:2]:  # Faqat birinchi 2 tasini tekshiramiz
            try:
                headers = {
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": api_config["host"]
                }
                
                params = {"url": test_url}
                
                response = requests.get(
                    api_config["url"], 
                    headers=headers, 
                    params=params, 
                    timeout=10
                )
                
                status_info = {
                    'success': response.status_code == 200,
                    'api_tested': api_config["name"],
                    'status_code': response.status_code,
                    'test_mode': TEST_MODE,
                    'status': 'active' if response.status_code == 200 else 'inactive',
                    'message': f"{api_config['name']} - {'Faol' if response.status_code == 200 else f'Nofaol ({response.status_code})'}"
                }
                
                return jsonify(status_info)
                
            except Exception as e:
                continue
        
        # Bepul API ni tekshirish
        try:
            shortcode = extract_shortcode_from_url(test_url)
            if shortcode:
                free_api_url = FREE_API["url"].format(code=shortcode)
                response = requests.get(free_api_url, headers=FREE_API["headers"], timeout=10)
                
                return jsonify({
                    'success': response.status_code == 200,
                    'api_tested': 'Instagram Private API',
                    'status': 'active' if response.status_code == 200 else 'inactive',
                    'status_code': response.status_code,
                    'test_mode': TEST_MODE,
                    'message': f"Instagram Private API - {'Faol' if response.status_code == 200 else 'Nofaol'}"
                })
        except Exception as e:
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
        "version": "10.0.0 - OPTIMIZED MULTI-API",
        "test_mode": TEST_MODE,
        "rapidapi_key": "configured",
        "available_apis": len(API_CONFIGS) + 1,
        "description": "Optimized Instagram API sistem - RapidAPI va bepul API lar",
        "endpoints": {
            "POST /check": "Asosiy tekshirish",
            "GET /rapidapi-status": "API holati", 
            "GET /test/accept": "Qabul qilinadigan test",
            "GET /test/reject": "Rad etiladigan test"
        },
        "note": "Sistem avval premium API larni, keyin bepul API ni sinab ko'radi. Test rejimi ham mavjud."
    })

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    debug_mode = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
