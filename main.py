from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
import json
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
    
    for hashtag in REQUIRED_HASHTAGS:
        if hashtag.lower() not in text_lower:
            logger.info(f"❌ Hashtag topilmadi: {hashtag}")
            return False
        else:
            logger.info(f"✅ Hashtag topildi: {hashtag}")
    
    logger.info("🎯 Ikkala hashtag ham topildi")
    return True

def extract_shortcode(url):
    """URL dan shortcode ni ajratish"""
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

def get_instagram_caption(url):
    """
    Instagram postdan caption ni olish - Haqiqiy usul
    """
    try:
        logger.info(f"🌐 Instagram post: {url}")
        
        # Shortcode ni olish
        shortcode = extract_shortcode(url)
        if not shortcode:
            logger.error("❌ Shortcode topilmadi")
            return ""
        
        # 1. Birinchi usul: Instagram API
        caption = get_caption_from_api(shortcode)
        if caption:
            return caption
        
        # 2. Ikkinchi usul: HTML dan extract qilish
        caption = get_caption_from_html(url)
        if caption:
            return caption
            
        # 3. Uchinchi usul: Meta tag lar
        caption = get_caption_from_meta(url)
        if caption:
            return caption
            
        logger.error("❌ Hech qanday usul bilan caption topilmadi")
        return ""
            
    except Exception as e:
        logger.error(f"💥 Xato: {e}")
        return ""

def get_caption_from_api(shortcode):
    """Instagram API orqali caption olish"""
    try:
        # Instagram o'z API si
        api_url = f"https://www.instagram.com/p/{shortcode}/?__a=1&__d=dis"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'X-IG-App-ID': '936619743392459',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        response = requests.get(api_url, headers=headers, timeout=15)
        logger.info(f"📊 API status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Turli strukturalarni tekshirish
            caption = extract_caption_from_json(data)
            if caption:
                logger.info("✅ API orqali caption topildi")
                return caption
                
        return ""
        
    except:
        return ""

def get_caption_from_html(url):
    """HTML dan caption ni extract qilish"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            html = response.text
            
            # JSON ma'lumotlarini qidirish
            json_patterns = [
                r'<script type="application/json"[^>]*>(.*?)</script>',
                r'window\._sharedData\s*=\s*({.*?});',
                r'{"config".*?"entry_data".*?}'
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, html, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        caption = extract_caption_from_json(data)
                        if caption:
                            logger.info("✅ HTML JSON dan caption topildi")
                            return caption
                    except:
                        continue
            
            # Meta description
            meta_pattern = r'<meta property="og:description" content="([^"]*)"'
            meta_match = re.search(meta_pattern, html)
            if meta_match:
                caption = meta_match.group(1)
                if caption and len(caption) > 10:
                    logger.info("✅ Meta description dan caption topildi")
                    return caption
        
        return ""
        
    except:
        return ""

def get_caption_from_meta(url):
    """Meta tag lar orqali caption olish"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Soddagina regex orqali
            patterns = [
                r'"caption":"([^"]*)"',
                r'"text":"([^"]*)"',
                r'"description":"([^"]*)"'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, response.text)
                for match in matches:
                    if match and len(match) > 10:
                        logger.info(f"✅ Regex orqali caption topildi: {pattern}")
                        return match
        
        return ""
        
    except:
        return ""

def extract_caption_from_json(data):
    """JSON ma'lumotlaridan caption ni extract qilish"""
    try:
        # Instagram strukturasi
        if isinstance(data, dict):
            # 1. Asosiy struktur
            posts = data.get('entry_data', {}).get('PostPage', [])
            if posts:
                media = posts[0].get('graphql', {}).get('shortcode_media', {})
                edges = media.get('edge_media_to_caption', {}).get('edges', [])
                if edges:
                    return edges[0].get('node', {}).get('text', '')
            
            # 2. items strukturasi
            items = data.get('items', [])
            if items:
                caption = items[0].get('caption', {}).get('text', '')
                if caption:
                    return caption
            
            # 3. Boshqa maydonlar
            for key in ['caption', 'text', 'description']:
                value = data.get(key)
                if value and isinstance(value, str) and len(value) > 10:
                    return value
                    
            # 4. Ichki qismlarni tekshirish
            if 'graphql' in data:
                media = data['graphql'].get('shortcode_media', {})
                edges = media.get('edge_media_to_caption', {}).get('edges', [])
                if edges:
                    return edges[0].get('node', {}).get('text', '')
                    
    except:
        pass
    return ""

@app.route('/', methods=['GET'])
def home():
    """API haqida ma'lumot"""
    return jsonify({
        "service": "Instagram Hashtag Checker API",
        "version": "5.0",
        "description": "Instagram postlardagi 2 ta maxsus hashtagni tekshiradi",
        "required_hashtags": ["#Telegramdagi", "#RekchiAi_bot"],
        "rules": "Ikkala hashtag ham bo'lishi shart",
        "endpoints": {
            "POST /check": "Hashtaglarni tekshirish",
            "GET /health": "Server holati"
        },
        "note": "Faqat haqiqiy Instagram postlarni tekshiradi. Test rejimi o'chirilgan."
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "Instagram Hashtag Checker"})

@app.route('/check', methods=['POST'])
def check_hashtags():
    """
    Asosiy tekshirish endpoint'i - FAQAT HAQIQIY POSTLAR
    """
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
        
        # Faqat Instagram URL larni qabul qilish
        if not re.search(r'instagram\.com/(p|reel|tv)/', url):
            return jsonify({
                "success": False,
                "approved": False,
                "error": "Faqat Instagram post URL lari qabul qilinadi"
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
    
    print("=" * 60)
    print("🎯 INSTAGRAM HASHTAG CHECKER API - REAL MODE")
    print("=" * 60)
    print(f"🚀 Server http://localhost:{port} da ishga tushmoqda...")
    print("📋 QIDIRILAYOTGAN HASHTAGLAR:")
    print("  1. #Telegramdagi")
    print("  2. #RekchiAi_bot")
    print("\n⚡ XUSUSIYATLAR:")
    print("  ✅ Faqat haqiqiy Instagram postlar")
    print("  ✅ Test rejimi O'CHIRILGAN")
    print("  ✅ 3 xil caption olish usuli")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False)
