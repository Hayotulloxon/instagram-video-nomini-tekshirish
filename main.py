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
    Instagram postdan caption ni olish - Private API orqali
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
        logger.info(f"🌐 Instagram post: {url}")
        
        # Shortcode ni olish
        shortcode = extract_shortcode(url)
        if not shortcode:
            logger.error("❌ Shortcode topilmadi")
            return ""
        
        # Instagram GraphQL API
        api_url = f"https://www.instagram.com/graphql/query/"
        
        # Query parametrlari
        params = {
            'query_hash': '2b0673e0dc4580674a88d426fe00ea90',
            'variables': json.dumps({
                'shortcode': shortcode,
                'child_comment_count': 3,
                'fetch_comment_count': 40,
                'parent_comment_count': 24,
                'has_threaded_comments': True
            })
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'X-IG-App-ID': '936619743392459',
            'Origin': 'https://www.instagram.com',
            'Referer': f'https://www.instagram.com/p/{shortcode}/',
        }
        
        response = requests.get(api_url, headers=headers, params=params, timeout=20)
        logger.info(f"📊 GraphQL status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Caption ni extract qilish
            edges = data.get('data', {}).get('shortcode_media', {}).get('edge_media_to_caption', {}).get('edges', [])
            if edges:
                caption = edges[0].get('node', {}).get('text', '')
                logger.info(f"✅ GraphQL orqali caption topildi: {len(caption)} belgi")
                return caption
        
        # Agar GraphQL ishlamasa, HTML dan extract qilish
        logger.info("🔄 GraphQL ishlamadi, HTML dan extract qilish...")
        return get_caption_from_html(url)
            
    except Exception as e:
        logger.error(f"💥 Xato: {e}")
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
            
            # 1. JSON-LD script larini qidirish
            script_pattern = r'<script type="application/ld\+json">(.*?)</script>'
            scripts = re.findall(script_pattern, html, re.DOTALL)
            
            for script in scripts:
                try:
                    data = json.loads(script)
                    caption = data.get('caption')
                    if caption:
                        logger.info("✅ JSON-LD dan caption topildi")
                        return caption
                except:
                    continue
            
            # 2. Meta description
            meta_pattern = r'<meta property="og:description" content="([^"]*)"'
            meta_match = re.search(meta_pattern, html)
            if meta_match:
                caption = meta_match.group(1)
                logger.info("✅ Meta description dan caption topildi")
                return caption
            
            # 3. window._sharedData
            shared_pattern = r'window\._sharedData\s*=\s*({.*?});'
            shared_match = re.search(shared_pattern, html, re.DOTALL)
            if shared_match:
                try:
                    data = json.loads(shared_match.group(1))
                    posts = data.get('entry_data', {}).get('PostPage', [])
                    if posts:
                        media = posts[0].get('graphql', {}).get('shortcode_media', {})
                        edges = media.get('edge_media_to_caption', {}).get('edges', [])
                        if edges:
                            caption = edges[0].get('node', {}).get('text', '')
                            logger.info("✅ SharedData dan caption topildi")
                            return caption
                except:
                    pass
        
        return ""
        
    except Exception as e:
        logger.error(f"💥 HTML parse xatosi: {e}")
        return ""

@app.route('/', methods=['GET'])
def home():
    """API haqida ma'lumot"""
    return jsonify({
        "service": "Instagram Hashtag Checker API",
        "version": "4.0", 
        "description": "Instagram postlardagi 2 ta maxsus hashtagni tekshiradi",
        "required_hashtags": ["#Telegramdagi", "#RekchiAi_bot"],
        "rules": "Ikkala hashtag ham bo'lishi shart",
        "api_method": "Instagram GraphQL + HTML Parsing",
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
