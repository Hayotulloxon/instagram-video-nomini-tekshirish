from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import re
import requests
import os

app = Flask(__name__)
CORS(app)

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    
    logger.info(f"🔍 Tekshirilayotgan matn: '{text}'")
    
    # Hashtaglarni tekshirish
    found_hashtags_list = extract_hashtags(text)
    found_hashtags_set = set([h.lower() for h in found_hashtags_list])
    
    logger.info(f"📌 Topilgan hashtaglar: {found_hashtags_set}")
    
    found_details = []
    all_found = True
    
    # Hashtaglarni tekshirish
    for hashtag in REQUIRED_HASHTAGS:
        required_lower = hashtag.lower()
        found = required_lower in found_hashtags_set
        
        logger.info(f"🏷️ Hashtag tekshirish: '{hashtag}' -> {found}")
        
        found_details.append({
            'hashtag': hashtag,
            'found': found,
            'required': True,
            'type': 'hashtag'
        })
        if not found:
            all_found = False
            logger.warning(f"❌ Hashtag topilmadi: {hashtag}")
    
    # Frazalarni tekshirish
    text_lower = (text or "").lower()
    
    for phrase in REQUIRED_PHRASES:
        phrase_lower = phrase.lower()
        found_phrase = phrase_lower in text_lower
        
        logger.info(f"📝 Fraza tekshirish: '{phrase}' -> {found_phrase}")
        
        found_details.append({
            'hashtag': phrase,
            'found': found_phrase,
            'required': True,
            'type': 'phrase'
        })
        if not found_phrase:
            all_found = False
            logger.warning(f"❌ Fraza topilmadi: {phrase}")
    
    logger.info(f"🎯 Yakuniy natija: {all_found}")
    return all_found, found_details

def get_instagram_post_info(video_url: str):
    """Instagram post ma'lumotlarini olish"""
    try:
        shortcode = extract_shortcode_from_url(video_url)
        if not shortcode:
            logger.error("❌ Instagram shortcode topilmadi")
            return None
            
        # Instagram Private API
        api_url = f"https://www.instagram.com/p/{shortcode}/?__a=1&__d=dis"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        logger.info(f"🌐 Instagram API so'rovi: {api_url}")
        response = requests.get(api_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ Instagram API muvaffaqiyatli ishladi")
            
            # Ma'lumotlarni parse qilish
            if 'graphql' in data and 'shortcode_media' in data['graphql']:
                media = data['graphql']['shortcode_media']
                
                # Caption olish
                caption = ""
                if 'edge_media_to_caption' in media:
                    edges = media['edge_media_to_caption']['edges']
                    if edges and len(edges) > 0:
                        caption = edges[0]['node'].get('text', '')
                
                # Likes olish
                likes = media.get('edge_media_preview_like', {}).get('count', 0)
                
                # Comments olish
                comments = media.get('edge_media_to_comment', {}).get('count', 0)
                
                return {
                    "message": "success",
                    "data": {
                        "caption": caption,
                        "likes": likes,
                        "comments": comments
                    },
                    "api_used": "REAL_INSTAGRAM_API"
                }
        
        logger.warning(f"❌ Instagram API xatosi: {response.status_code}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Instagram ma'lumot olish xatosi: {str(e)}")
        return None

def get_test_instagram_data(video_url: str):
    """Test ma'lumotlari"""
    try:
        # Avval haqiqiy ma'lumotlarni olishga harakat qilamiz
        real_data = get_instagram_post_info(video_url)
        if real_data:
            return real_data
        
        # Agar haqiqiy ma'lumot olinmasa, test ma'lumotlari
        # URL dan test turini aniqlaymiz
        url_lower = (video_url or "").lower()
        
        # Agar URL da "reject" yoki "false" bo'lsa, rad etish
        if "reject" in url_lower or "false" in url_lower or "nohashtag" in url_lower:
            return {
                "message": "success",
                "data": {
                    "caption": "Bu oddiy video hech qanday hashtag yoq #boshqa #hashtag",
                    "likes": 100,
                    "comments": 15
                },
                "api_used": "TEST_MODE_REJECT"
            }
        # Agar URL da "accept" yoki "true" bo'lsa, qabul qilish
        elif "accept" in url_lower or "true" in url_lower or "hashtag" in url_lower:
            return {
                "message": "success",
                "data": {
                    "caption": "Bu test video Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot",
                    "likes": 150,
                    "comments": 25
                },
                "api_used": "TEST_MODE_ACCEPT"
            }
        else:
            # Default holat - test rejimi (qabul qilinmaydi)
            return {
                "message": "success",
                "data": {
                    "caption": "Bu video hech qanday maxsus hashtag yoq #oddiy #video",
                    "likes": 80,
                    "comments": 10
                },
                "api_used": "TEST_MODE_DEFAULT_REJECT"
            }
            
    except Exception as e:
        logger.error(f"❌ Test ma'lumot olish xatosi: {str(e)}")
        # Xato bo'lsa ham rad etiladigan test qaytaramiz
        return {
            "message": "success",
            "data": {
                "caption": "Xato yuz berdi, video rad etildi #xato #video",
                "likes": 0,
                "comments": 0
            },
            "api_used": "TEST_MODE_ERROR"
        }

@app.route('/', methods=['GET'])
def home():
    """API haqida ma'lumot"""
    return jsonify({
        'service': 'Instagram Video Text Checker API',
        'version': '2.0',
        'description': 'Instagram post caption ichidagi hashtag va frazalarni tekshiradi',
        'requirements': [
            '2 ta hashtag: #Telegramdagi, #RekchiAi_bot',
            '2 ta fraza: Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?',
            'Telegramga RekchiAi_bot ga kiring.'
        ],
        'endpoints': {
            'POST /check': {
                'description': 'Video matnni tekshirish',
                'parameters': {
                    'video_url': 'Instagram video URL (majburiy)'
                }
            },
            'GET /health': 'Server holatini tekshirish',
            'GET /test/accept': 'Qabul qilinadigan test',
            'GET /test/reject': 'Rad etiladigan test',
            'POST /manual-check': 'Qo\'lda matn tekshirish'
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """Server holatini tekshirish"""
    return jsonify({
        'status': 'ok',
        'service': 'Instagram Video Text Checker API',
        'version': '2.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/check', methods=['POST'])
def check_video():
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
                'test_mode': True
            }), 400
            
        video_url = data.get('video_url')
        
        if not video_url:
            return jsonify({
                'success': False,
                'approved': False,
                'error': 'video_url maydoni talab qilinadi',
                'warning': None,
                'fine_amount': 0,
                'test_mode': True
            }), 400
        
        logger.info(f"🎬 Video tekshirish so'rovi: {video_url}")
        
        # Instagram ma'lumotlarini olish
        instagram_data = get_test_instagram_data(video_url)
        
        if instagram_data.get('message') != 'success':
            error_msg = instagram_data.get('error') or 'Instagram ma\'lumotlarini olish mumkin emas'
            return jsonify({
                'success': False,
                'approved': False,
                'error': error_msg,
                'warning': 'API xatosi',
                'fine_amount': 0,
                'test_mode': True
            }), 400
        
        # API dan qaytgan ma'lumotlarni olish
        api_data = instagram_data.get('data', {})
        api_used = instagram_data.get('api_used', 'UNKNOWN')
        
        caption_text = api_data.get('caption', '')
        like_count = api_data.get('likes', 0)
        comment_count = api_data.get('comments', 0)
        
        logger.info(f"📄 Caption text olingan: '{caption_text}'")
        
        # Hashtag va frazalarni tekshirish
        has_required_hashtags, found_hashtags = check_required_hashtags(caption_text)
        
        response_data = {
            'success': True,
            'approved': has_required_hashtags,
            'error': None if has_required_hashtags else 'Kerakli hashtag yoki frazalar topilmadi',
            'warning': None if has_required_hashtags else 'Video rad etildi - jarima qo\'llaniladi',
            'fine_amount': 0 if has_required_hashtags else 10000,
            'test_mode': "REAL" if "REAL" in api_used else "TEST",
            'api_used': api_used,
            'hashtags_check': found_hashtags,
            'post_stats': {
                'likes': like_count,
                'comments': comment_count
            },
            'caption': caption_text,
            'message': 'Video qabul qilindi - barcha shartlar bajarilgan' if has_required_hashtags else 'Video rad etildi - barcha shartlar bajarilmagan'
        }
        
        logger.info(f"🎯 Yakuniy javob: approved = {has_required_hashtags}")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"❌ Video check error: {str(e)}")
        return jsonify({
            'success': False,
            'approved': False,
            'error': f"Server xatosi: {str(e)}",
            'warning': None,
            'fine_amount': 0,
            'test_mode': True
        }), 500

@app.route('/test/accept', methods=['GET', 'POST'])
def test_accept():
    """Qabul qilinadigan test"""
    test_data = {
        "message": "success",
        "data": {
            "caption": "Bu test video Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot",
            "likes": 150,
            "comments": 25
        },
        "api_used": "TEST_ENDPOINT_ACCEPT"
    }
    
    api_data = test_data.get('data', {})
    caption_text = api_data.get('caption', '')
    like_count = api_data.get('likes', 0)
    comment_count = api_data.get('comments', 0)
    
    has_required_hashtags, found_hashtags = check_required_hashtags(caption_text)
    
    return jsonify({
        'success': True,
        'approved': has_required_hashtags,
        'error': None,
        'warning': None,
        'fine_amount': 0,
        'test_mode': True,
        'api_used': 'TEST_ENDPOINT_ACCEPT',
        'message': 'Bu test video qabul qilinadi - barcha shartlar bajarilgan',
        'hashtags_check': found_hashtags,
        'post_stats': {
            'likes': like_count,
            'comments': comment_count
        },
        'caption': caption_text
    })

@app.route('/test/reject', methods=['GET', 'POST'])
def test_reject():
    """Rad etiladigan test"""
    test_data = {
        "message": "success",
        "data": {
            "caption": "Bu oddiy video hech qanday hashtag yoq #boshqa #hashtag",
            "likes": 100,
            "comments": 15
        },
        "api_used": "TEST_ENDPOINT_REJECT"
    }
    
    api_data = test_data.get('data', {})
    caption_text = api_data.get('caption', '')
    like_count = api_data.get('likes', 0)
    comment_count = api_data.get('comments', 0)
    
    has_required_hashtags, found_hashtags = check_required_hashtags(caption_text)
    
    return jsonify({
        'success': True,
        'approved': has_required_hashtags,
        'error': 'Kerakli hashtag yoki frazalar topilmadi',
        'warning': 'Video rad etildi - 10,000 jarima',
        'fine_amount': 10000,
        'test_mode': True,
        'api_used': 'TEST_ENDPOINT_REJECT',
        'message': 'Bu test video rad etildi - barcha shartlar bajarilmagan',
        'hashtags_check': found_hashtags,
        'post_stats': {
            'likes': like_count,
            'comments': comment_count
        },
        'caption': caption_text
    })

@app.route('/manual-check', methods=['POST'])
def manual_check():
    """Qo'lda matn kiritish orqali tekshirish"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON ma\'lumotlari talab qilinadi'
            }), 400
            
        caption_text = data.get('caption', '')
        
        if not caption_text:
            return jsonify({
                'success': False,
                'error': 'caption maydoni talab qilinadi'
            }), 400
        
        has_required_hashtags, found_hashtags = check_required_hashtags(caption_text)
        
        return jsonify({
            'success': True,
            'approved': has_required_hashtags,
            'hashtags_check': found_hashtags,
            'caption': caption_text,
            'message': 'Matn qabul qilindi' if has_required_hashtags else 'Matn rad etildi'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Server xatosi: {str(e)}"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print("=" * 60)
    print("Instagram Video Text Checker API")
    print("=" * 60)
    print(f"Server http://localhost:{port} da ishga tushmoqda...")
    print("\nEndpoint'lar:")
    print("  GET  /              - API haqida ma'lumot")
    print("  GET  /health        - Server holati")
    print("  POST /check         - Video tekshirish")
    print("  GET  /test/accept   - Qabul qilinadigan test")
    print("  GET  /test/reject   - Rad etiladigan test")
    print("  POST /manual-check  - Qo'lda matn tekshirish")
    print("\n" + "=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False)
