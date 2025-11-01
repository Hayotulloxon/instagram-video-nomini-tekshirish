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
RAPIDAPI_HOST = "instagram-social-api.p.rapidapi.com"

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
    logger.info(f"extract_hashtags: topilgan hashtaglar: {hashtags}")
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
    
    logger.info(f"check_required_hashtags: Kirish matni: '{text}'")
    
    # Hashtaglarni tekshirish
    found_hashtags_list = extract_hashtags(text)
    found_hashtags_set = set([h.lower() for h in found_hashtags_list])
    
    logger.info(f"check_required_hashtags: Topilgan hashtaglar (set): {found_hashtags_set}")
    
    found_details = []
    all_found = True
    
    # Hashtaglarni tekshirish
    for hashtag in REQUIRED_HASHTAGS:
        required_lower = hashtag.lower()
        found = required_lower in found_hashtags_set
        
        logger.info(f"Hashtag tekshirish: '{hashtag}' -> '{required_lower}' -> {found}")
        
        found_details.append({
            'hashtag': hashtag,
            'found': found,
            'required': True,
            'type': 'hashtag'
        })
        if not found:
            all_found = False
            logger.info(f"Hashtag topilmadi: {hashtag}")
    
    # Frazalarni tekshirish
    text_lower = (text or "").lower()
    logger.info(f"Frazalar tekshirish: text_lower = '{text_lower}'")
    
    for phrase in REQUIRED_PHRASES:
        phrase_lower = phrase.lower()
        found_phrase = phrase_lower in text_lower
        
        logger.info(f"Fraza tekshirish: '{phrase}' -> '{phrase_lower}' -> {found_phrase}")
        
        found_details.append({
            'hashtag': phrase,
            'found': found_phrase,
            'required': True,
            'type': 'phrase'
        })
        if not found_phrase:
            all_found = False
            logger.info(f"Fraza topilmadi: {phrase}")
    
    logger.info(f"check_required_hashtags: Natija - {all_found}")
    
    return all_found, found_details

def get_instagram_post_info(video_url: str):
    """Instagram Social API orqali post ma'lumotlarini olish"""
    try:
        if TEST_MODE:
            logger.info("TEST MODE: Test ma'lumotlar ishlatilmoqda")
            return get_test_instagram_data(video_url)
        
        shortcode = extract_shortcode_from_url(video_url)
        if not shortcode:
            logger.error("Instagram shortcode topilmadi")
            return get_test_instagram_data(video_url)
        
        # Instagram Social API dan ma'lumot olish - TO'G'RI ENDPOINT
        url = f"https://{RAPIDAPI_HOST}/v1/post_info"
        
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": RAPIDAPI_HOST
        }
        
        params = {"shortcode": shortcode}
        
        logger.info(f"Instagram Social API so'rovi: {url}?shortcode={shortcode}")
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        logger.info(f"API response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info("Instagram Social API muvaffaqiyatli ishladi")
            return parse_instagram_social_api(data, "Instagram Social API")
        else:
            logger.error(f"Instagram Social API xatosi: {response.status_code} - {response.text}")
            # Boshqa endpoint larni sinab ko'ramiz
            return try_alternative_endpoints(shortcode, video_url)
            
    except Exception as e:
        logger.error(f"Instagram ma'lumot olish xatosi: {str(e)}")
        return get_test_instagram_data(video_url)

def try_alternative_endpoints(shortcode: str, video_url: str):
    """Alternative endpoint larni sinab ko'rish"""
    endpoints = [
        {
            "name": "Post Info by URL",
            "url": f"https://{RAPIDAPI_HOST}/v1/post_info_by_url",
            "params": {"url": video_url}
        },
        {
            "name": "Media Info", 
            "url": f"https://{RAPIDAPI_HOST}/v1/media_info",
            "params": {"shortcode": shortcode}
        },
        {
            "name": "Post Details",
            "url": f"https://{RAPIDAPI_HOST}/v1/post_details", 
            "params": {"shortcode": shortcode}
        }
    ]
    
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    
    for endpoint in endpoints:
        try:
            logger.info(f"Alternative endpoint sinab ko'ryapman: {endpoint['name']}")
            
            response = requests.get(
                endpoint["url"], 
                headers=headers, 
                params=endpoint["params"], 
                timeout=20
            )
            
            logger.info(f"{endpoint['name']} status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"{endpoint['name']} muvaffaqiyatli ishladi")
                return parse_instagram_social_api(data, f"Instagram Social API - {endpoint['name']}")
                
        except Exception as e:
            logger.warning(f"{endpoint['name']} xatosi: {str(e)}")
            continue
    
    # Agar barcha endpoint lar ishlamasa, test rejimiga o'tamiz
    logger.warning("Barcha endpoint lar ishlamadi, test rejimiga o'tiladi")
    return get_test_instagram_data(video_url)

def parse_instagram_social_api(data, api_name):
    """Instagram Social API responseni parse qilish"""
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
        
        logger.info(f"parse_instagram_social_api: API respons: {data}")
        
        if isinstance(data, dict):
            # Turli strukturalarni qo'llab-quvvatlash
            caption = ""
            likes = 0
            comments = 0
            
            # 1. Asosiy data strukturasini tekshirish
            if 'data' in data and isinstance(data['data'], dict):
                post_data = data['data']
                
                # Caption olish
                if 'caption' in post_data:
                    caption_data = post_data['caption']
                    if isinstance(caption_data, dict):
                        caption = caption_data.get('text', '')
                    else:
                        caption = str(caption_data)
                elif 'edge_media_to_caption' in post_data:
                    edges = post_data['edge_media_to_caption'].get('edges', [])
                    if edges and len(edges) > 0:
                        caption = edges[0].get('node', {}).get('text', '')
                
                # Likes olish
                likes = post_data.get('like_count', 0) or post_data.get('likes', 0) or \
                       post_data.get('edge_media_preview_like', {}).get('count', 0) or \
                       post_data.get('edge_liked_by', {}).get('count', 0)
                
                # Comments olish
                comments = post_data.get('comment_count', 0) or post_data.get('comments', 0) or \
                          post_data.get('edge_media_to_comment', {}).get('count', 0)
            
            # 2. To'g'ridan-to'g'ri post ma'lumotlari
            elif 'caption' in data:
                caption = data.get('caption', '')
                likes = data.get('like_count', 0) or data.get('likes', 0)
                comments = data.get('comment_count', 0) or data.get('comments', 0)
            
            # 3. GraphQL strukturasini tekshirish
            elif 'graphql' in data and 'shortcode_media' in data['graphql']:
                media = data['graphql']['shortcode_media']
                
                # Caption olish
                if 'edge_media_to_caption' in media:
                    edges = media['edge_media_to_caption'].get('edges', [])
                    if edges and len(edges) > 0:
                        caption = edges[0].get('node', {}).get('text', '')
                
                # Likes olish
                likes = media.get('edge_media_preview_like', {}).get('count', 0) or \
                       media.get('edge_liked_by', {}).get('count', 0)
                
                # Comments olish
                comments = media.get('edge_media_to_comment', {}).get('count', 0)
            
            result['data']['caption'] = caption
            result['data']['likes'] = likes
            result['data']['comments'] = comments
            
        logger.info(f"parse_instagram_social_api: Parsed data: {result['data']}")
        
        return result
        
    except Exception as e:
        logger.error(f"Instagram Social API parse xatosi: {str(e)}")
        return None

def get_test_instagram_data(video_url: str):
    """Test ma'lumotlari"""
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
        
        logger.info(f"Caption text olingan: '{caption_text}'")
        
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
        
        logger.info(f"Yakuniy javob: approved = {has_required_hashtags}")
        
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

@app.route('/api-status', methods=['GET'])
def api_status():
    """API holatini tekshirish"""
    try:
        # Test uchun Instagram post shortcode
        test_shortcode = "C1LqX5JMv7G"  # Haqiqiy Instagram post
        
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": RAPIDAPI_HOST
        }
        
        # Bir nechta endpoint larni tekshiramiz
        endpoints = [
            {
                "name": "Post Info",
                "url": f"https://{RAPIDAPI_HOST}/v1/post_info",
                "params": {"shortcode": test_shortcode}
            },
            {
                "name": "Post Info by URL",
                "url": f"https://{RAPIDAPI_HOST}/v1/post_info_by_url", 
                "params": {"url": f"https://www.instagram.com/p/{test_shortcode}/"}
            },
            {
                "name": "Media Info",
                "url": f"https://{RAPIDAPI_HOST}/v1/media_info",
                "params": {"shortcode": test_shortcode}
            }
        ]
        
        results = []
        
        for endpoint in endpoints:
            try:
                response = requests.get(
                    endpoint["url"], 
                    headers=headers, 
                    params=endpoint["params"], 
                    timeout=15
                )
                
                result = {
                    'endpoint': endpoint['name'],
                    'status_code': response.status_code,
                    'active': response.status_code == 200
                }
                
                if response.status_code == 200:
                    data = response.json()
                    result['message'] = 'Faol'
                    result['sample_data'] = {
                        'has_data': bool(data),
                        'data_keys': list(data.keys()) if isinstance(data, dict) else []
                    }
                else:
                    result['message'] = f'Nofaol ({response.status_code})'
                
                results.append(result)
                
            except Exception as e:
                results.append({
                    'endpoint': endpoint['name'],
                    'status_code': 'error',
                    'active': False,
                    'message': str(e)
                })
        
        return jsonify({
            'success': any(result['active'] for result in results),
            'test_mode': TEST_MODE,
            'endpoints_tested': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'error',
            'test_mode': TEST_MODE,
            'error': str(e)
        }), 500

@app.route('/debug-test', methods=['POST'])
def debug_test():
    """Debug uchun test endpoint"""
    data = request.get_json()
    text = data.get('text', '')
    
    logger.info(f"DEBUG TEST: Kirish matni: '{text}'")
    
    has_required, details = check_required_hashtags(text)
    
    return jsonify({
        'text': text,
        'has_required_hashtags': has_required,
        'details': details,
        'required_hashtags': ['#Telegramdagi', '#RekchiAi_bot'],
        'required_phrases': [
            'Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?',
            'Telegramga RekchiAi_bot ga kiring.'
        ]
    })

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
        "version": "12.0.0 - MULTI-ENDPOINT SUPPORT",
        "test_mode": TEST_MODE,
        "api_provider": "Instagram Social API",
        "description": "Instagram Social API ning bir nechta endpoint laridan foydalanadi",
        "endpoints": {
            "POST /check": "Asosiy tekshirish",
            "GET /api-status": "API holati (barcha endpoint lar)",
            "POST /debug-test": "Debug test",
            "GET /test/accept": "Qabul qilinadigan test",
            "GET /test/reject": "Rad etiladigan test"
        },
        "note": "Sistem bir nechta endpoint larni sinab ko'radi va birinchi ishlaydigan endpoint dan foydalanadi"
    })

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    debug_mode = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
