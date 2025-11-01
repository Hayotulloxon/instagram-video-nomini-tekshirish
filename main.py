from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
import os
import logging
import json

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
    Instagram postdan caption ni olish - YANGILANGAN VERSIYA
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
        
        html_content = response.text
        
        # YANGI: JSON ma'lumotlarini qidirish
        json_patterns = [
            r'{"config":.*?"entry_data":.*?}',
            r'window\._sharedData\s*=\s*({.*?});',
            r'<script type="application/json".*?>(.*?)</script>'
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, html_content, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    caption = extract_caption_from_json(data)
                    if caption:
                        logger.info(f"✅ JSON dan caption topildi")
                        return caption
                except:
                    continue
        
        # YANGI: Meta tag larni tekshirish
        meta_patterns = [
            r'<meta property="og:description" content="([^"]*)"',
            r'<meta name="description" content="([^"]*)"',
            r'"caption":"([^"]*)"',
            r'"text":"([^"]*)"'
        ]
        
        for pattern in meta_patterns:
            matches = re.findall(pattern, html_content)
            for match in matches:
                if match and len(match) > 10:  # Kamida 10 belgi bo'lsin
                    logger.info(f"✅ Regex orqali caption topildi: {pattern}")
                    return match
        
        logger.warning("❌ Hech qanday usul bilan caption topilmadi")
        return ""
        
    except Exception as e:
        logger.error(f"💥 Xato: {e}")
        return ""

def extract_caption_from_json(data):
    """JSON ma'lumotlaridan caption ni extract qilish"""
    try:
        # Turli JSON strukturalari
        if isinstance(data, dict):
            # 1. entry_data -> PostPage
            posts = data.get('entry_data', {}).get('PostPage', [])
            if posts:
                media = posts[0].get('graphql', {}).get('shortcode_media', {})
                edges = media.get('edge_media_to_caption', {}).get('edges', [])
                if edges:
                    return edges[0].get('node', {}).get('text', '')
            
            # 2. tobirama strukturasi
            caption = data.get('caption')
            if caption:
                return caption
                
            # 3. Boshqa maydonlar
            for key in ['text', 'description', 'title']:
                value = data.get(key)
                if value and isinstance(value, str) and len(value) > 10:
                    return value
                    
    except:
        pass
    return ""

@app.route('/', methods=['GET'])
def home():
    """API haqida ma'lumot"""
    return jsonify({
        "service": "Instagram Hashtag Checker API",
        "version": "2.0",
        "description": "Instagram postlardagi 2 ta maxsus hashtagni tekshiradi",
        "required_hashtags": ["#Telegramdagi", "#RekchiAi_bot"],
        "rules": "Ikkala hashtag ham bo'lishi shart",
        "endpoints": {
            "POST /check": "Hashtaglarni tekshirish",
            "GET /health": "Server holati"
        }
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "Instagram Hashtag Checker"})

@app.route('/check', methods=['POST'])
def check_hashtags():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "approved": False,
                "error": "JSON ma'lumotlari talab qilinadi"
            }), 400
        
        url = data.get('url') or data.get('video_url')
        
        if not url:
            return jsonify({
                "success": False,
                "approved": False,
                "error": "URL maydoni talab qilinadi"
            }), 400
        
        logger.info(f"🎬 Yangi so'rov: {url}")
        
        caption = get_instagram_caption(url)
        
        if not caption:
            return jsonify({
                "success": False,
                "approved": False,
                "error": "Caption topilmadi yoki post mavjud emas"
            }), 404
        
        has_required_hashtags = check_required_hashtags(caption)
        
        return jsonify({
            "success": True,
            "approved": has_required_hashtags,
            "hashtags_found": has_required_hashtags,
            "required_hashtags": ["#Telegramdagi", "#RekchiAi_bot"],
            "caption_preview": caption[:150] + "..." if len(caption) > 150 else caption,
            "caption_length": len(caption),
            "message": "✅ Video qabul qilindi - ikkala hashtag topildi" if has_required_hashtags else "❌ Video rad etildi - hashtaglar topilmadi"
        })
        
    except Exception as e:
        logger.error(f"💥 Server xatosi: {e}")
        return jsonify({
            "success": False,
            "approved": False,
            "error": f"Server xatosi: {str(e)}"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
