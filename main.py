from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
import os
import logging

app = Flask(__name__)
CORS(app)

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RapidAPI konfiguratsiyasi
RAPIDAPI_KEY = "82d6cdc0f2mshd3d57d3979430d8p19ec3bjsnde8d982c9e90"
RAPIDAPI_HOST = "instagram-downloader-download-instagram-videos-stories1.p.rapidapi.com"

def check_required_hashtags(text):
    """
    Matndan kerakli 2 ta hashtag borligini tekshirish
    """
    REQUIRED_HASHTAGS = ["#Telegramdagi", "#RekchiAi_bot"]
    
    if not text:
        logger.info("❌ Matn bo'sh")
        return False
    
    text_lower = text.lower()
    found_hashtags = []
    
    for hashtag in REQUIRED_HASHTAGS:
        if hashtag.lower() in text_lower:
            found_hashtags.append(hashtag)
            logger.info(f"✅ Hashtag topildi: {hashtag}")
        else:
            logger.info(f"❌ Hashtag topilmadi: {hashtag}")
    
    # Ikkala hashtag ham topilishi kerak
    all_found = len(found_hashtags) == len(REQUIRED_HASHTAGS)
    logger.info(f"🎯 Hashtaglar holati: {found_hashtags} -> {all_found}")
    
    return all_found

def get_instagram_caption(url):
    """
    Instagram postdan caption ni olish - RapidAPI orqali
    """
    try:
        # Test holatlari
        url_lower = url.lower()
        
        if "test_accept" in url_lower:
            logger.info("🔧 TEST MODE: Qabul qilinadigan test")
            return "Bu test video #Telegramdagi #RekchiAi_bot bilan ishlaydi"
        
        elif "test_reject" in url_lower:
            logger.info("🔧 TEST MODE: Rad etiladigan test") 
            return "Bu oddiy video #boshqa hashtag"
        
        # Haqiqiy Instagram post - RapidAPI orqali
        logger.info(f"🌐 RapidAPI orqali Instagram post: {url}")
        
        api_url = "https://instagram-downloader-download-instagram-videos-stories1.p.rapidapi.com/"
        
        querystring = {"url": url}
        
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": RAPIDAPI_HOST
        }
        
        response = requests.get(api_url, headers=headers, params=querystring, timeout=20)
        logger.info(f"📊 RapidAPI status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            caption = data.get('caption', '')
            logger.info(f"✅ RapidAPI orqali caption topildi: {len(caption)} belgi")
            return caption
        else:
            logger.error(f"❌ RapidAPI xatosi: {response.status_code} - {response.text}")
            return ""
            
    except requests.exceptions.Timeout:
        logger.error("⏰ RapidAPI so'rovi vaqti tugadi")
        return ""
    except requests.exceptions.ConnectionError:
        logger.error("🔌 Internet aloqasi xatosi")
        return ""
    except Exception as e:
        logger.error(f"💥 RapidAPI xatosi: {e}")
        return ""

@app.route('/', methods=['GET'])
def home():
    """API haqida ma'lumot"""
    return jsonify({
        "service": "Instagram Hashtag Checker API",
        "version": "3.0",
        "description": "Instagram postlardagi 2 ta maxsus hashtagni tekshiradi (RapidAPI orqali)",
        "required_hashtags": ["#Telegramdagi", "#RekchiAi_bot"],
        "rules": "Ikkala hashtag ham bo'lishi shart",
        "api_provider": "RapidAPI - Instagram Downloader",
        "endpoints": {
            "POST /check": "Hashtaglarni tekshirish",
            "GET /health": "Server holati"
        },
        "test_urls": {
            "test_accept": "Qabul qilinadigan test",
            "test_reject": "Rad etiladigan test"
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """Server holatini tekshirish"""
    return jsonify({
        "status": "ok",
        "service": "Instagram Hashtag Checker",
        "version": "3.0",
        "api_provider": "RapidAPI"
    })

@app.route('/check', methods=['POST'])
def check_hashtags():
    """
    Asosiy tekshirish endpoint'i
    """
    try:
        # JSON ma'lumotni olish
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "approved": False,
                "error": "JSON ma'lumotlari talab qilinadi"
            }), 400
        
        # URL ni olish
        url = data.get('url') or data.get('video_url')
        
        if not url:
            return jsonify({
                "success": False,
                "approved": False,
                "error": "URL maydoni talab qilinadi (url yoki video_url)"
            }), 400
        
        logger.info(f"🎬 Yangi so'rov: {url}")
        
        # Instagram caption ni olish
        caption = get_instagram_caption(url)
        
        if not caption:
            return jsonify({
                "success": False,
                "approved": False,
                "error": "Caption topilmadi yoki post mavjud emas"
            }), 404
        
        # Hashtaglarni tekshirish
        has_required_hashtags = check_required_hashtags(caption)
        
        # Javobni tayyorlash
        response_data = {
            "success": True,
            "approved": has_required_hashtags,
            "hashtags_found": has_required_hashtags,
            "required_hashtags": ["#Telegramdagi", "#RekchiAi_bot"],
            "caption_preview": caption[:150] + "..." if len(caption) > 150 else caption,
            "caption_length": len(caption),
            "api_used": "RAPIDAPI",
            "message": "✅ Video qabul qilindi - ikkala hashtag topildi" if has_required_hashtags else "❌ Video rad etildi - hashtaglar topilmadi"
        }
        
        logger.info(f"🎯 Yakuniy natija: {has_required_hashtags}")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"💥 Server xatosi: {e}")
        return jsonify({
            "success": False,
            "approved": False,
            "error": f"Server xatosi: {str(e)}"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    
    print("=" * 60)
    print("🎯 INSTAGRAM HASHTAG CHECKER API - RAPIDAPI VERSION")
    print("=" * 60)
    print(f"🚀 Server http://localhost:{port} da ishga tushmoqda...")
    print(f"🔑 API Provider: RapidAPI")
    print("\n📋 QIDIRILAYOTGAN HASHTAGLAR:")
    print("  1. #Telegramdagi")
    print("  2. #RekchiAi_bot")
    print("\n📡 ENDPOINT'LAR:")
    print("  POST /check  - Hashtaglarni tekshirish")
    print("  GET  /health - Server holati")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False)
