from flask import Flask, request, jsonify
import logging
import re

app = Flask(__name__)

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# TEST MODE - Haqiqiy tekshirish o'rniga URL ga qarab qaror qiladi
TEST_MODE = True

def analyze_url_for_hashtags(video_url: str):
    """
    URL ni tahlil qilib, hashtag bor/yo'qligini aniqlash
    """
    # Hashtag li deb hisoblangan URL patternlari
    positive_patterns = [
        "instagram.com/p/",  # Postlar
        "instagram.com/reel/",  # Reelllar  
        "hashtag",  # Hashtag so'zi
        "rekchi",  # Rekchi so'zi
        "bot"  # Bot so'zi
    ]
    
    # Hashtag yoq deb hisoblangan URL patternlari
    negative_patterns = [
        "example.com",
        "test.com", 
        "nohashtag"
    ]
    
    video_url_lower = video_url.lower()
    
    # Avval negative patterns ni tekshiramiz
    for pattern in negative_patterns:
        if pattern in video_url_lower:
            return False
    
    # Keyin positive patterns ni tekshiramiz
    for pattern in positive_patterns:
        if pattern in video_url_lower:
            return True
    
    # Agar hech qaysi pattern mos kelmasa, default = True (qabul qilamiz)
    return True

@app.route('/check', methods=['POST'])
def check_video_text():
    """
    Video havolasida kerakli hashtag borligini tekshirish
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'has_text': False,
                'error': 'JSON ma\'lumotlari talab qilinadi'
            }), 400
            
        video_url = data.get('video_url')
        
        if not video_url:
            return jsonify({
                'success': False,
                'has_text': False,
                'error': 'video_url maydoni talab qilinadi'
            }), 400
        
        logger.info(f"Video tekshirish so'rovi: {video_url}")
        
        # TEST MODE: URL ni tahlil qilamiz
        has_hashtags = analyze_url_for_hashtags(video_url)
        
        # Hashtag formatida kerakli matn
        REQUIRED_HASHTAGS = [
            "#Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring.",
            "#Telegramdagi", 
            "#RekchiAi_bot"
        ]
        
        # Test rejimida URL ga qarab qaytaramiz
        found_hashtags = []
        for hashtag in REQUIRED_HASHTAGS:
            found_hashtags.append({
                'hashtag': hashtag,
                'found': has_hashtags  # Barchasi bir xil
            })
        
        return jsonify({
            'success': True,
            'has_text': has_hashtags,
            'title': 'Instagram Video',
            'found_hashtags': found_hashtags,
            'test_mode': True,
            'url_analysis': {
                'has_hashtags': has_hashtags,
                'reason': 'URL tahlili asosida'
            },
            'error': None
        })
        
    except Exception as e:
        logger.error(f"Video check error: {str(e)}")
        return jsonify({
            'success': False,
            'has_text': False,
            'error': f"Server xatosi: {str(e)}"
        }), 500

@app.route('/test/accept')
def test_accept():
    """Hashtag li test - QABUL QILINADI"""
    return jsonify({
        'success': True,
        'has_text': True,
        'title': 'Test Video - Qabul qilindi',
        'test_mode': True,
        'message': 'Bu test video qabul qilinadi'
    })

@app.route('/test/reject')
def test_reject():
    """Hashtag siz test - RAD ETILADI"""
    return jsonify({
        'success': True,
        'has_text': False, 
        'title': 'Test Video - Rad etildi',
        'test_mode': True,
        'message': 'Bu test video rad etildi'
    })

@app.route('/')
def root():
    """Asosiy sahifa"""
    return jsonify({
        "message": "Instagram Video Check API",
        "version": "4.0.0 - SMART TEST MODE",
        "test_mode": True,
        "description": "URL tahlili asosida ishlaydi",
        "endpoints": {
            "POST /check": "Video hashtaglarini tekshirish",
            "GET /test/accept": "Qabul qilinadigan test",
            "GET /test/reject": "Rad etiladigan test"
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
