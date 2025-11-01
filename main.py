from flask import Flask, request, jsonify
import logging
import re
import os

app = Flask(__name__)

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    """Matnni normalizatsiya qilish - ortiqcha bo'sh joylarni olib tashlash"""
    if not text:
        return ""
    # Ortiqcha bo'sh joylarni bitta bo'sh joy bilan almashtirish
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_hashtags(text: str):
    """Matndan hashtaglarni topish (Unicode qo'llab-quvvatlash bilan)"""
    if not text:
        return []
    
    # # bilan boshlanadigan so'zlarni topish (kirill va lotin harflar)
    hashtags = re.findall(r'#[\w\u0400-\u04FF]+', text, re.UNICODE)
    # Kichik harflarga o'tkazish
    return [h.lower() for h in hashtags]

def check_required_content(text: str):
    """
    Matndan kerakli hashtag va frazalarni tekshirish
    MUKAMMAL ALGORITM - har bir element aniq tekshiriladi
    """
    if not text:
        logger.warning("⚠️ Bo'sh matn yuborilgan!")
        return False, []
    
    # Matnni normalizatsiya qilish
    text_normalized = normalize_text(text)
    text_lower = text_normalized.lower()
    
    logger.info("=" * 70)
    logger.info("🔍 TEKSHIRISH BOSHLANDI")
    logger.info("=" * 70)
    logger.info(f"📝 Matn: {text_normalized[:200]}...")
    logger.info("-" * 70)
    
    # Kerakli elementlar ro'yxati
    REQUIRED_ITEMS = [
        {
            'type': 'hashtag',
            'value': '#telegramdagi',
            'display': '#Telegramdagi',
            'description': 'Hashtag #Telegramdagi'
        },
        {
            'type': 'hashtag',
            'value': '#rekchiai_bot',
            'display': '#RekchiAi_bot',
            'description': 'Hashtag #RekchiAi_bot'
        },
        {
            'type': 'phrase',
            'value': 'videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?',
            'display': 'Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?',
            'description': 'Fraza "Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?"'
        },
        {
            'type': 'phrase',
            'value': 'telegramga rekchiai_bot ga kiring',
            'display': 'Telegramga RekchiAi_bot ga kiring',
            'description': 'Fraza "Telegramga RekchiAi_bot ga kiring"'
        }
    ]
    
    found_details = []
    all_found = True
    
    # Hashtaglarni topish
    found_hashtags = extract_hashtags(text)
    logger.info(f"📌 Topilgan hashtaglar: {found_hashtags}")
    logger.info("-" * 70)
    
    # Har bir kerakli elementni tekshirish
    for index, item in enumerate(REQUIRED_ITEMS, 1):
        if item['type'] == 'hashtag':
            # Hashtag tekshirish
            found = item['value'] in found_hashtags
            icon = "✅" if found else "❌"
            
            logger.info(f"{icon} [{index}/4] {item['description']}")
            logger.info(f"     Qidirilgan: '{item['value']}'")
            logger.info(f"     Natija: {'TOPILDI ✓' if found else 'TOPILMADI ✗'}")
            
        else:  # phrase
            # Frazani tekshirish - kichik harflarda
            phrase_lower = item['value'].lower()
            found = phrase_lower in text_lower
            icon = "✅" if found else "❌"
            
            logger.info(f"{icon} [{index}/4] {item['description']}")
            logger.info(f"     Qidirilgan: '{phrase_lower}'")
            logger.info(f"     Natija: {'TOPILDI ✓' if found else 'TOPILMADI ✗'}")
        
        logger.info("-" * 70)
        
        found_details.append({
            'item': item['display'],
            'type': item['type'],
            'required': True,
            'found': found,
            'description': item['description']
        })
        
        if not found:
            all_found = False
    
    # Yakuniy natija
    if all_found:
        logger.info("🎉 YAKUNIY NATIJA: ✅ BARCHA SHARTLAR BAJARILGAN!")
    else:
        logger.info("⛔ YAKUNIY NATIJA: ❌ BA'ZI SHARTLAR BAJARILMAGAN")
    
    logger.info("=" * 70)
    
    return all_found, found_details

@app.route('/check', methods=['POST'])
def check_video():
    """
    Asosiy tekshirish endpoint
    Caption matnini to'g'ridan-to'g'ri tekshiradi
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'approved': False,
                'error': 'JSON ma\'lumotlari talab qilinadi',
                'fine_amount': 0
            }), 400
        
        # Caption matnini olish
        caption = data.get('caption', '')
        
        if not caption:
            return jsonify({
                'success': False,
                'approved': False,
                'error': 'caption maydoni talab qilinadi',
                'fine_amount': 0
            }), 400
        
        logger.info(f"📥 Yangi so'rov keldi")
        
        # Matnni tekshirish
        has_required, found_items = check_required_content(caption)
        
        # Javob tayyorlash
        if has_required:
            response = {
                'success': True,
                'approved': True,
                'error': None,
                'warning': None,
                'fine_amount': 0,
                'message': '🎉 Video qabul qilindi - barcha shartlar bajarilgan!',
                'required_items_check': found_items,
                'caption': caption
            }
        else:
            response = {
                'success': True,
                'approved': False,
                'error': 'Kerakli hashtag yoki frazalar topilmadi',
                'warning': '⚠️ Video rad etildi - jarima qo\'llaniladi',
                'fine_amount': 10000,
                'message': '❌ Video rad etildi - ba\'zi shartlar bajarilmagan',
                'required_items_check': found_items,
                'caption': caption
            }
        
        logger.info(f"📤 Javob yuborildi: approved={has_required}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"❌ Server xatosi: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'approved': False,
            'error': f"Server xatosi: {str(e)}",
            'fine_amount': 0
        }), 500

@app.route('/test/correct', methods=['GET', 'POST'])
def test_correct():
    """To'g'ri matn bilan test (qabul qilinadi)"""
    caption = """Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot"""
    
    has_required, found_items = check_required_content(caption)
    
    return jsonify({
        'success': True,
        'approved': has_required,
        'error': None,
        'warning': None,
        'fine_amount': 0,
        'test_type': 'CORRECT_TEXT',
        'message': '✅ Bu test QABUL QILINADI',
        'required_items_check': found_items,
        'caption': caption
    })

@app.route('/test/incorrect', methods=['GET', 'POST'])
def test_incorrect():
    """Noto'g'ri matn bilan test (rad etiladi)"""
    caption = "Bu oddiy video hech qanday kerakli hashtag yoq #boshqa #hashtag"
    
    has_required, found_items = check_required_content(caption)
    
    return jsonify({
        'success': True,
        'approved': has_required,
        'error': 'Kerakli hashtag yoki frazalar topilmadi',
        'warning': '⚠️ Video rad etildi - 10,000 so\'m jarima',
        'fine_amount': 10000,
        'test_type': 'INCORRECT_TEXT',
        'message': '❌ Bu test RAD ETILADI',
        'required_items_check': found_items,
        'caption': caption
    })

@app.route('/test/partial', methods=['GET', 'POST'])
def test_partial():
    """Qisman to'g'ri matn bilan test (faqat hashtaglar)"""
    caption = "Mening video #Telegramdagi #RekchiAi_bot bu yerda"
    
    has_required, found_items = check_required_content(caption)
    
    return jsonify({
        'success': True,
        'approved': has_required,
        'error': 'Kerakli frazalar topilmadi' if not has_required else None,
        'warning': '⚠️ Video rad etildi - frazalar yo\'q' if not has_required else None,
        'fine_amount': 10000 if not has_required else 0,
        'test_type': 'PARTIAL_TEXT',
        'message': '❌ Bu test RAD ETILADI (faqat hashtag, frazalar yo\'q)',
        'required_items_check': found_items,
        'caption': caption
    })

@app.route('/test/all', methods=['GET'])
def test_all():
    """Barcha test holatlarini ko'rsatish"""
    tests = []
    
    # Test 1: To'g'ri
    caption1 = "Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot"
    approved1, items1 = check_required_content(caption1)
    tests.append({
        'test_name': 'Test 1: TO\'G\'RI MATN',
        'approved': approved1,
        'caption': caption1,
        'items': items1
    })
    
    # Test 2: Noto'g'ri
    caption2 = "Bu oddiy video #boshqa #hashtag"
    approved2, items2 = check_required_content(caption2)
    tests.append({
        'test_name': 'Test 2: NOTO\'G\'RI MATN',
        'approved': approved2,
        'caption': caption2,
        'items': items2
    })
    
    # Test 3: Qisman
    caption3 = "Mening video #Telegramdagi #RekchiAi_bot"
    approved3, items3 = check_required_content(caption3)
    tests.append({
        'test_name': 'Test 3: QISMAN TO\'G\'RI (faqat hashtag)',
        'approved': approved3,
        'caption': caption3,
        'items': items3
    })
    
    return jsonify({
        'message': 'Barcha testlar',
        'tests': tests,
        'summary': {
            'total': 3,
            'passed': sum(1 for t in tests if t['approved']),
            'failed': sum(1 for t in tests if not t['approved'])
        }
    })

@app.route('/')
def root():
    """Asosiy sahifa - API ma'lumotlari"""
    return jsonify({
        "app_name": "Instagram Video Validator",
        "version": "4.0.0 - API SIZ MUKAMMAL",
        "status": "🟢 ACTIVE",
        "description": "Caption matnini to'g'ridan-to'g'ri tekshiradi, API kerak emas!",
        
        "requirements": {
            "hashtags": [
                "#Telegramdagi",
                "#RekchiAi_bot"
            ],
            "phrases": [
                "Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi?",
                "Telegramga RekchiAi_bot ga kiring"
            ],
            "note": "BARCHA 4 ta element (2 hashtag + 2 fraza) bo'lishi SHART!"
        },
        
        "endpoints": {
            "POST /check": {
                "description": "Asosiy tekshirish",
                "method": "POST",
                "body": {
                    "caption": "Matn..."
                },
                "example": {
                    "caption": "Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot"
                }
            },
            "GET /test/correct": "✅ To'g'ri matn testi",
            "GET /test/incorrect": "❌ Noto'g'ri matn testi",
            "GET /test/partial": "⚠️ Qisman to'g'ri matn testi",
            "GET /test/all": "📊 Barcha testlar"
        },
        
        "usage_examples": {
            "curl": 'curl -X POST http://localhost:10000/check -H "Content-Type: application/json" -d \'{"caption":"Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot"}\'',
            "python": """
import requests

response = requests.post('http://localhost:10000/check', json={
    'caption': 'Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot'
})
print(response.json())
"""
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """Server holati"""
    return jsonify({
        'status': 'healthy',
        'message': 'Server ishlayapti',
        'version': '4.0.0'
    })

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    logger.info("=" * 70)
    logger.info("🚀 Instagram Video Validator ishga tushdi!")
    logger.info(f"📍 Port: {port}")
    logger.info(f"🌐 URL: http://localhost:{port}")
    logger.info("=" * 70)
    app.run(host="0.0.0.0", port=port, debug=True)
