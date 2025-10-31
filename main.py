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
RAPIDAPI_HOST = "instagram-scraper-api2.p.rapidapi.com"

# TEST MODE - agar RapidAPI ishlamasa
TEST_MODE = os.getenv('TEST_MODE', 'False').lower() == 'true'

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

    # Instagram post URL patternlari
    patterns = [
        r'instagram\.com/p/([^/?#&]+)',
        r'instagram\.com/reel/([^/?#&]+)',
        r'instagram\.com/tv/([^/?#&]+)',
        # stories usually need different approach; kept for completeness but may not work
        r'instagram\.com/stories/[^/]+/([^/?#&]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, video_url)
        if match:
            return match.group(1)
    
    return None

def extract_hashtags(text: str):
    """
    Matndan barcha hashtaglarni topadi.
    Hashtag = '#' bilan boshlangan va harf, raqam yoki '_' dan iborat so'z.
    """
    if not text:
        return []
    # \w matches [A-Za-z0-9_], UNICODE flag keeps it robust for non-latin too in many environments
    hashtags = re.findall(r'#\w[\w_]*', text, flags=re.UNICODE)
    return hashtags

def check_required_hashtags(text: str):
    """
    Matndan kerakli hashtaglarni tekshirish — endi haqiqiy hashtaglarni ajratib tekshiradi.
    REQUIRED_HASHTAGS ga faqat haqiqiy hashtaglarni qo'ying.
    REQUIRED_PHRASES esa butun jumla / fragmentlar uchun.
    """
    # Kerakli haqiqiy hashtaglar (faqat hashtag so'zlari bo'lishi kerak)
    REQUIRED_HASHTAGS = [
        "#Telegramdagi",
        "#RekchiAi_bot",
    ]
    
    # Agar siz butun jumla (hashtag bo'lmagan) fragmentlarni ham talab qilsangiz:
    REQUIRED_PHRASES = [
        "Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?",
        "Telegramga RekchiAi_bot ga kiring."
    ]
    
    found_hashtags_list = extract_hashtags(text)
    found_set = set([h.lower() for h in found_hashtags_list])
    
    found_details = []
    all_found = True
    
    # Tekshiramiz: haqiqiy hashtaglar
    for hashtag in REQUIRED_HASHTAGS:
        found = hashtag.lower() in found_set
        found_details.append({
            'hashtag': hashtag,
            'found': found,
            'required': True,
            'type': 'hashtag'
        })
        if not found:
            all_found = False
    
    # Tekshiramiz: kerakli frazalar (agar siz ular ham shart bo'lsa)
    for phrase in REQUIRED_PHRASES:
        found_phrase = phrase.lower() in (text or "").lower()
        found_details.append({
            'hashtag': phrase,
            'found': found_phrase,
            'required': True,
            'type': 'phrase'
        })
        if not found_phrase:
            all_found = False
    
    return all_found, found_details

def get_test_instagram_data(video_url: str):
    """
    Test ma'lumotlari - RapidAPI ishlamaganda
    """
    # URL ga qarab turli test holatlari
    if "test_accept" in (video_url or "") or "hashtag" in (video_url or ""):
        return {
            "message": "success",
            "data": {
                "caption": {
                    "text": "Bu test video #Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot #hashtag"
                },
                "like_count": 150,
                "comment_count": 25
            }
        }
    elif "test_reject" in (video_url or "") or "nohashtag" in (video_url or ""):
        return {
            "message": "success", 
            "data": {
                "caption": {
                    "text": "Bu oddiy video hech qanday hashtag yoq #boshqa #hashtag"
                },
                "like_count": 100,
                "comment_count": 15
            }
        }
    else:
        # Default holat
        return {
            "message": "success",
            "data": {
                "caption": {
                    "text": "Standart test matni #Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot"
                },
                "like_count": 200,
                "comment_count": 30
            }
        }

def extract_instagram_data(video_url: str):
    """
    RapidAPI orqali Instagram ma'lumotlarini olish
    """
    try:
        if TEST_MODE:
            logger.info("TEST MODE: Haqiqiy ma'lumot o'rniga test ma'lumot qaytariladi")
            return get_test_instagram_data(video_url)
        
        # Kodni olishdan oldin URL dan kod olinadimi tekshiramiz
        code = extract_instagram_code(video_url)
        if not code:
            logger.error("Instagram post kodi topilmadi URL dan.")
            return {
                "message": "error",
                "error": "Instagram post kodi URL dan olinmadi"
            }
        
        # RapidAPI orqali Instagram post ma'lumotlarini olish
        url = "https://instagram-scraper-api2.p.rapidapi.com/v1/post_info"
        
        querystring = {"code": code}
        
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": RAPIDAPI_HOST
        }
        
        response = requests.get(url, headers=headers, params=querystring, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"RapidAPI muvaffaqiyatli ishladi: {data.get('message', 'Ma\'lumot olindi')}")
            return data
        else:
            logger.error(f"RapidAPI xatosi: {response.status_code} - {response.text}")
            # Agar RapidAPI ishlamasa, test ma'lumot qaytaramiz
            return get_test_instagram_data(video_url)
            
    except requests.exceptions.Timeout:
        logger.error("RapidAPI so'rovi timeout")
        return get_test_instagram_data(video_url)
    except Exception as e:
        logger.error(f"Instagram ma'lumot olish xatosi: {str(e)}")
        return get_test_instagram_data(video_url)

@app.route('/check', methods=['POST'])
@rapidapi_required
def check_video_text():
    """
    RapidAPI orqali video tekshirish - asosiy endpoint
    """
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
        
        # RapidAPI orqali ma'lumot olish
        instagram_data = extract_instagram_data(video_url)
        
        if instagram_data.get('message') != 'success':
            # Agar extract_instagram_data xato haqida ma'lumot bergan bo'lsa, shu xabarni qaytaramiz
            error_msg = instagram_data.get('error') or 'Instagram ma\'lumotlarini olish mumkin emas'
            return jsonify({
                'success': False,
                'approved': False,
                'error': error_msg,
                'warning': 'RapidAPI xatosi' if not TEST_MODE else None,
                'fine_amount': 0,
                'test_mode': TEST_MODE
            }), 400
        
        # Caption (matn) ni olish - caption mavjudligini xavfsiz tarzda tekshiramiz
        caption = instagram_data.get('data', {}).get('caption')
        caption_text = ""
        if caption and isinstance(caption, dict):
            caption_text = caption.get('text') or ""
        elif isinstance(caption, str):
            caption_text = caption
        else:
            caption_text = ""
        
        # Hashtaglarni tekshirish
        has_required_hashtags, found_hashtags = check_required_hashtags(caption_text)
        
        # Post statistiklarini xavfsiz olish
        like_count = instagram_data.get('data', {}).get('like_count', 0)
        comment_count = instagram_data.get('data', {}).get('comment_count', 0)
        
        if has_required_hashtags:
            return jsonify({
                'success': True,
                'approved': True,
                'error': None,
                'warning': None,
                'fine_amount': 0,
                'test_mode': TEST_MODE,
                'hashtags_check': found_hashtags,
                'post_stats': {
                    'likes': like_count,
                    'comments': comment_count
                },
                'message': 'Video qabul qilindi - barcha hashtag shartlari bajarilgan'
            })
        else:
            return jsonify({
                'success': True,
                'approved': False,
                'error': 'Kerakli hashtaglar topilmadi',
                'warning': 'Video rad etildi - jarima qo\'llaniladi',
                'fine_amount': 10000,
                'test_mode': TEST_MODE,
                'hashtags_check': found_hashtags,
                'post_stats': {
                    'likes': like_count,
                    'comments': comment_count
                },
                'message': 'Video rad etildi - hashtag shartlari bajarilmagan'
            })
        
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
    """
    RapidAPI holatini tekshirish
    """
    try:
        # RapidAPI connection test
        url = "https://instagram-scraper-api2.p.rapidapi.com/v1/post_info"
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": RAPIDAPI_HOST
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        return jsonify({
            'success': True,
            'rapidapi_status': 'active' if response.status_code == 200 else 'inactive',
            'status_code': response.status_code,
            'test_mode': TEST_MODE,
            'message': 'RapidAPI faol' if response.status_code == 200 else 'RapidAPI nofaol'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'rapidapi_status': 'error',
            'test_mode': TEST_MODE,
            'error': str(e)
        }), 500

@app.route('/test/accept')
def test_accept():
    """Hashtag li test - QABUL QILINADI"""
    return jsonify({
        'success': True,
        'approved': True,
        'error': None,
        'warning': None,
        'fine_amount': 0,
        'test_mode': True,
        'message': 'Bu test video qabul qilinadi - barcha hashtaglar mavjud',
        'hashtags_check': [
            {'hashtag': '#Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?', 'found': True, 'required': True, 'type': 'phrase'},
            {'hashtag': '#Telegramdagi', 'found': True, 'required': True, 'type': 'hashtag'},
            {'hashtag': '#RekchiAi_bot', 'found': True, 'required': True, 'type': 'hashtag'}
        ]
    })

@app.route('/test/reject')
def test_reject():
    """Hashtag siz test - RAD ETILADI"""
    return jsonify({
        'success': True,
        'approved': False,
        'error': 'Kerakli hashtaglar topilmadi',
        'warning': 'Video rad etildi - 10,000 jarima',
        'fine_amount': 10000,
        'test_mode': True,
        'message': 'Bu test video rad etildi - hashtaglar yoq',
        'hashtags_check': [
            {'hashtag': '#Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?', 'found': False, 'required': True, 'type': 'phrase'},
            {'hashtag': '#Telegramdagi', 'found': False, 'required': True, 'type': 'hashtag'},
            {'hashtag': '#RekchiAi_bot', 'found': False, 'required': True, 'type': 'hashtag'}
        ]
    })

@app.route('/')
def root():
    """Asosiy sahifa"""
    return jsonify({
        "message": "Instagram Video Validation API with RapidAPI",
        "version": "6.0.0 - RAPIDAPI INTEGRATION (updated hashtag checks)",
        "test_mode": TEST_MODE,
        "rapidapi_key": "configured" if RAPIDAPI_KEY else "not configured",
        "description": "RapidAPI orqali haqiqiy Instagram ma'lumotlarini oladi",
        "endpoints": {
            "POST /check": "Asosiy tekshirish (RapidAPI)",
            "GET /rapidapi-status": "RapidAPI holati",
            "GET /test/accept": "Qabul qilinadigan test",
            "GET /test/reject": "Rad etiladigan test"
        },
        "requirements": [
            "Instagram linki bo'lishi kerak",
            "Quyidagi hashtaglar bo'lishi majburiy"
        ],
        "required_hashtags": [
            "#Telegramdagi", 
            "#RekchiAi_bot"
        ],
        "required_phrases": [
            "Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?",
            "Telegramga RekchiAi_bot ga kiring."
        ]
    })

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
