from flask import Flask, request, jsonify
import logging
import re
import requests
import os

app = Flask(__name__)

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

def normalize_text(text: str) -> str:
    """Matnni normalizatsiya qilish - bo'sh joylar, kichik harflar"""
    if not text:
        return ""
    # Ortiqcha bo'sh joylarni olib tashlash
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_hashtags(text: str):
    """Matndan hashtaglarni topish"""
    if not text:
        return []
    
    # # bilan boshlanadigan so'zlarni topish (Unicode qo'llab-quvvatlash bilan)
    hashtags = re.findall(r'#[\w\u0400-\u04FF]+', text, re.UNICODE)
    return [h.lower() for h in hashtags]

def check_required_content(text: str):
    """
    Matndan kerakli hashtag va frazalarni tekshirish
    MUKAMMAL VERSIYA - har bir element alohida tekshiriladi
    """
    if not text:
        logger.warning("Bo'sh matn yuborilgan!")
        return False, []
    
    # Matnni normalizatsiya qilish
    text_normalized = normalize_text(text)
    text_lower = text_normalized.lower()
    
    logger.info(f"="*60)
    logger.info(f"TEKSHIRILAYOTGAN MATN:")
    logger.info(f"{text_normalized}")
    logger.info(f"="*60)
    
    # Kerakli elementlar
    REQUIRED_ITEMS = [
        {
            'type': 'hashtag',
            'value': '#telegramdagi',
            'display': '#Telegramdagi',
            'description': 'Hashtag: #Telegramdagi'
        },
        {
            'type': 'hashtag',
            'value': '#rekchiai_bot',
            'display': '#RekchiAi_bot',
            'description': 'Hashtag: #RekchiAi_bot'
        },
        {
            'type': 'phrase',
            'value': 'videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?',
            'display': 'Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?',
            'description': 'Fraza: "Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?"'
        },
        {
            'type': 'phrase',
            'value': 'telegramga rekchiai_bot ga kiring',
            'display': 'Telegramga RekchiAi_bot ga kiring',
            'description': 'Fraza: "Telegramga RekchiAi_bot ga kiring"'
        }
    ]
    
    found_details = []
    all_found = True
    
    # Hashtaglarni topish
    found_hashtags = extract_hashtags(text)
    logger.info(f"Topilgan barcha hashtaglar: {found_hashtags}")
    
    # Har bir kerakli elementni tekshirish
    for item in REQUIRED_ITEMS:
        if item['type'] == 'hashtag':
            # Hashtag tekshirish
            found = item['value'] in found_hashtags
            
            logger.info(f"✓ Tekshirish: {item['description']}")
            logger.info(f"  Qidirilayotgan: '{item['value']}'")
            logger.info(f"  Natija: {'✅ TOPILDI' if found else '❌ TOPILMADI'}")
            
        else:  # phrase
            # Frazani tekshirish - kichik harflarda
            phrase_lower = item['value'].lower()
            found = phrase_lower in text_lower
            
            logger.info(f"✓ Tekshirish: {item['description']}")
            logger.info(f"  Qidirilayotgan: '{phrase_lower}'")
            logger.info(f"  Natija: {'✅ TOPILDI' if found else '❌ TOPILMADI'}")
        
        found_details.append({
            'item': item['display'],
            'type': item['type'],
            'required': True,
            'found': found,
            'description': item['description']
        })
        
        if not found:
            all_found = False
    
    logger.info(f"="*60)
    logger.info(f"YAKUNIY NATIJA: {'✅ BARCHA SHARTLAR BAJARILGAN' if all_found else '❌ BA\'ZI SHARTLAR BAJARILMAGAN'}")
    logger.info(f"="*60)
    
    return all_found, found_details

def get_instagram_post_info(video_url: str):
    """
    Instagram post ma'lumotlarini olish
    REAL API Integration + Test Mode
    """
    try:
        # URL dan holatni aniqlash (test rejimi)
        url_lower = (video_url or "").lower()
        
        # Test rejimi - URL ichida maxsus kalit so'zlar bor bo'lsa
        if "test" in url_lower or "example.com" in url_lower:
            logger.info("TEST REJIMI faollashtirildi")
            
            if "reject" in url_lower or "nohashtag" in url_lower:
                return {
                    "message": "success",
                    "data": {
                        "caption": "Bu oddiy video hech qanday kerakli hashtag yoq #boshqa #hashtag",
                        "likes": 100,
                        "comments": 15
                    },
                    "api_used": "TEST_MODE_REJECT"
                }
            else:
                # Test accept
                return {
                    "message": "success",
                    "data": {
                        "caption": "Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot",
                        "likes": 150,
                        "comments": 25
                    },
                    "api_used": "TEST_MODE_ACCEPT"
                }
        
        # REAL API Integration
        # Instagram shortcode olish
        shortcode = extract_shortcode_from_url(video_url)
        if not shortcode:
            return {
                "message": "error",
                "error": "Noto'g'ri Instagram URL"
            }
        
        logger.info(f"Shortcode topildi: {shortcode}")
        
        # REAL API so'rovi - RapidAPI yoki boshqa Instagram API
        # Bu yerda sizning API key va endpoint'ingizni qo'shing
        
        # VARIANT 1: RapidAPI - Instagram API
        api_key = os.environ.get('RAPIDAPI_KEY', '')
        
        if api_key:
            headers = {
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "instagram-scraper-api2.p.rapidapi.com"
            }
            
            api_url = f"https://instagram-scraper-api2.p.rapidapi.com/v1/post_info"
            params = {"code_or_id_or_url": shortcode}
            
            response = requests.get(api_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # API dan ma'lumotlarni parse qilish
                caption = data.get('data', {}).get('caption', {}).get('text', '')
                likes = data.get('data', {}).get('like_count', 0)
                comments = data.get('data', {}).get('comment_count', 0)
                
                return {
                    "message": "success",
                    "data": {
                        "caption": caption,
                        "likes": likes,
                        "comments": comments
                    },
                    "api_used": "RAPIDAPI_INSTAGRAM"
                }
        
        # Agar API key yo'q bo'lsa - xatolik qaytarish
        return {
            "message": "error",
            "error": "Instagram API key sozlanmagan. RAPIDAPI_KEY environment o'zgaruvchisini sozlang."
        }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API so'rov xatosi: {str(e)}")
        return {
            "message": "error",
            "error": f"API xatosi: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Umumiy xato: {str(e)}")
        return {
            "message": "error",
            "error": f"Xatolik yuz berdi: {str(e)}"
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
                'fine_amount': 0
            }), 400
            
        video_url = data.get('video_url')
        
        if not video_url:
            return jsonify({
                'success': False,
                'approved': False,
                'error': 'video_url maydoni talab qilinadi',
                'warning': None,
                'fine_amount': 0
            }), 400
        
        logger.info(f"Video tekshirish so'rovi: {video_url}")
        
        # Instagram ma'lumotlarini olish
        instagram_data = get_instagram_post_info(video_url)
        
        if instagram_data.get('message') != 'success':
            error_msg = instagram_data.get('error', 'Instagram ma\'lumotlarini olish mumkin emas')
            return jsonify({
                'success': False,
                'approved': False,
                'error': error_msg,
                'warning': 'API xatosi yuz berdi',
                'fine_amount': 0
            }), 400
        
        # API dan qaytgan ma'lumotlarni olish
        api_data = instagram_data.get('data', {})
        api_used = instagram_data.get('api_used', 'UNKNOWN')
        
        caption_text = api_data.get('caption', '')
        like_count = api_data.get('likes', 0)
        comment_count = api_data.get('comments', 0)
        
        logger.info(f"Caption text olingan: '{caption_text}'")
        
        # Hashtag va frazalarni tekshirish
        has_required_content, found_items = check_required_content(caption_text)
        
        # Javob tayyorlash
        if has_required_content:
            message = '✅ Video qabul qilindi - barcha shartlar bajarilgan!'
            error = None
            warning = None
            fine_amount = 0
        else:
            message = '❌ Video rad etildi - ba\'zi shartlar bajarilmagan'
            error = 'Kerakli hashtag yoki frazalar topilmadi'
            warning = '⚠️ Video rad etildi - jarima qo\'llaniladi'
            fine_amount = 10000
        
        response_data = {
            'success': True,
            'approved': has_required_content,
            'error': error,
            'warning': warning,
            'fine_amount': fine_amount,
            'api_used': api_used,
            'required_items_check': found_items,
            'post_stats': {
                'likes': like_count,
                'comments': comment_count
            },
            'caption': caption_text,
            'message': message
        }
        
        logger.info(f"Yakuniy javob: approved = {has_required_content}")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Video check error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'approved': False,
            'error': f"Server xatosi: {str(e)}",
            'warning': None,
            'fine_amount': 0
        }), 500

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
        
        has_required_content, found_items = check_required_content(caption_text)
        
        return jsonify({
            'success': True,
            'approved': has_required_content,
            'required_items_check': found_items,
            'caption': caption_text,
            'message': '✅ Matn qabul qilindi' if has_required_content else '❌ Matn rad etildi',
            'fine_amount': 0 if has_required_content else 10000
        })
        
    except Exception as e:
        logger.error(f"Manual check error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f"Server xatosi: {str(e)}"
        }), 500

@app.route('/test/accept', methods=['GET', 'POST'])
def test_accept():
    """Qabul qilinadigan test"""
    caption = "Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot"
    
    has_required, found_items = check_required_content(caption)
    
    return jsonify({
        'success': True,
        'approved': has_required,
        'error': None,
        'warning': None,
        'fine_amount': 0,
        'test_mode': True,
        'message': '✅ Bu test video qabul qilinadi',
        'required_items_check': found_items,
        'post_stats': {'likes': 150, 'comments': 25},
        'caption': caption
    })

@app.route('/test/reject', methods=['GET', 'POST'])
def test_reject():
    """Rad etiladigan test"""
    caption = "Bu oddiy video hech qanday kerakli hashtag yoq #boshqa #hashtag"
    
    has_required, found_items = check_required_content(caption)
    
    return jsonify({
        'success': True,
        'approved': has_required,
        'error': 'Kerakli hashtag yoki frazalar topilmadi',
        'warning': '⚠️ Video rad etildi - 10,000 so\'m jarima',
        'fine_amount': 10000,
        'test_mode': True,
        'message': '❌ Bu test video rad etildi',
        'required_items_check': found_items,
        'post_stats': {'likes': 100, 'comments': 15},
        'caption': caption
    })

@app.route('/')
def root():
    """Asosiy sahifa"""
    return jsonify({
        "message": "Instagram Video Validation API - MUKAMMAL VERSIYA",
        "version": "3.0.0 - PERFECT",
        "status": "Active ✅",
        "description": "Mukammal tekshirish tizimi - har doim to'g'ri ishlaydi",
        "requirements": {
            "hashtags": [
                "#Telegramdagi",
                "#RekchiAi_bot"
            ],
            "phrases": [
                "Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?",
                "Telegramga RekchiAi_bot ga kiring"
            ]
        },
        "endpoints": {
            "POST /check": "Asosiy tekshirish (video_url beriladi)",
            "POST /manual-check": "Qo'lda matn tekshirish (caption beriladi)",
            "GET /test/accept": "Qabul qilinadigan test",
            "GET /test/reject": "Rad etiladigan test"
        },
        "api_setup": {
            "note": "Real Instagram API ishlatish uchun RAPIDAPI_KEY environment o'zgaruvchisini sozlang",
            "example": "export RAPIDAPI_KEY='your_api_key_here'"
        },
        "test_examples": {
            "qabul_qilinadigan": {
                "url": "https://example.com/test_accept",
                "caption": "Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot"
            },
            "rad_etiladigan": {
                "url": "https://example.com/test_reject",
                "caption": "Bu oddiy video hech qanday kerakli hashtag yoq"
            }
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
