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
    Instagram postdan caption ni olish
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
        
        # Haqiqiy Instagram post
        logger.info(f"🌐 Haqiqiy Instagram post: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        logger.info(f"📊 Instagram status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"❌ Instagram xatosi: {response.status_code}")
            return ""
        
        # 1. Meta description orqali
        meta_match = re.search(r'<meta property="og:description" content="([^"]*)"', response.text)
        if meta_match:
            caption = meta_match.group(1)
            logger.info("✅ Meta description orqali caption topildi")
            return caption
        
        # 2. JSON-LD orqali
        json_match = re.search(r'"caption":"([^"]*)"', response.text)
        if json_match:
            caption = json_match.group(1)
            logger.info("✅ JSON-LD orqali caption topildi")
            return caption
        
        # 3. window._sharedData orqali
        shared_match = re.search(r'window\._sharedData\s*=\s*({.*?});', response.text, re.DOTALL)
        if shared_match:
            try:
                import json
                shared_data = json.loads(shared_match.group(1))
                
                # Caption ni extract qilish
                posts = shared_data.get('entry_data', {}).get('PostPage', [])
                if posts:
                    media = posts[0].get('graphql', {}).get('shortcode_media', {})
                    edges = media.get('edge_media_to_caption', {}).get('edges', [])
                    if edges:
                        caption = edges[0].get('node', {}).get('text', '')
                        logger.info("✅ SharedData orqali caption topildi")
                        return caption
            except Exception as e:
                logger.warning(f"⚠️ SharedData parse xatosi: {e}")
        
        logger.warning("❌ Hech qanday usul bilan caption topilmadi")
        return ""
        
    except requests.exceptions.Timeout:
        logger.error("⏰ Instagram so'rovi vaqti tugadi")
        return ""
    except requests.exceptions.ConnectionError:
        logger.error("🔌 Internet aloqasi xatosi")
        return ""
    except Exception as e:
        logger.error(f"💥 Umumiy xato: {e}")
        return ""

@app.route('/', methods=['GET'])
def home():
    """API haqida ma'lumot"""
    return jsonify({
        "service": "Instagram Hashtag Checker API",
        "version": "1.0",
        "description": "Instagram postlardagi 2 ta maxsus hashtagni tekshiradi",
        "required_hashtags": [
            "#Telegramdagi",
            "#RekchiAi_bot"
        ],
        "rules": "Ikkala hashtag ham bo'lishi shart. Kamida bittasi bo'lmasa, video rad etiladi.",
        "endpoints": {
            "POST /check": {
                "description": "Hashtaglarni tekshirish",
                "parameters": {
                    "url": "Instagram post URL (majburiy)",
                    "video_url": "Instagram video URL (alternativ)"
                }
            },
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
        "version": "1.0"
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
    print("🎯 INSTAGRAM HASHTAG CHECKER API")
    print("=" * 60)
    print(f"🚀 Server http://localhost:{port} da ishga tushmoqda...")
    print("\n📋 QIDIRILAYOTGAN HASHTAGLAR:")
    print("  1. #Telegramdagi")
    print("  2. #RekchiAi_bot")
    print("\n📡 ENDPOINT'LAR:")
    print("  POST /check  - Hashtaglarni tekshirish")
    print("  GET  /health - Server holati")
    print("  GET  /       - API haqida ma'lumot")
    print("\n🔧 TEST QILISH:")
    print('  curl -X POST http://localhost:10000/check \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"url": "test_accept"}\'')
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False)
