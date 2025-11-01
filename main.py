from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import logging
import os

app = Flask(__name__)
CORS(app)

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Instagram API token
INSTAGRAM_API_URL = "https://insta.savetube.me/downloadPostPic"
API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXlsb2FkIjoiVXNlciIsImlhdCI6MTcxMzQ1NTI4MSwiZXhwIjoxNzEzNDU1MzExfQ.quApDi178e9PEGtf6qY_QI2sgnKxVrl1ErcLO4oS8fw"

def get_instagram_post_data(instagram_url):
    """Instagram post ma'lumotlarini olish"""
    try:
        headers = {
            'Accept': '*/*',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        data = {
            'url': instagram_url
        }
        
        logger.info(f"📡 Instagram API so'rovi: {instagram_url}")
        
        response = requests.post(
            INSTAGRAM_API_URL,
            json=data,
            headers=headers,
            timeout=30
        )
        
        logger.info(f"📊 API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ Instagram API muvaffaqiyatli ishladi")
            return data
        else:
            logger.error(f"❌ API xatosi: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ API so'rovi xatosi: {e}")
        return None

def check_required_text(post_data, target_text):
    """Post ma'lumotlarida kerakli matn borligini tekshirish"""
    try:
        # Turli maydonlarda matn qidirish
        caption = post_data.get('caption', '')
        description = post_data.get('description', '')
        text = post_data.get('text', '')
        
        # Barcha matnlarni birlashtirish
        all_text = f"{caption} {description} {text}".lower()
        target_lower = target_text.lower()
        
        found = target_lower in all_text
        
        logger.info(f"🔍 Tekshirish: '{target_text}' -> {found}")
        
        return found
        
    except Exception as e:
        logger.error(f"❌ Matn tekshirish xatosi: {e}")
        return False

@app.route('/', methods=['GET'])
def home():
    """API haqida ma'lumot"""
    return jsonify({
        'service': 'Instagram Video Checker API',
        'version': '3.0',
        'description': 'Instagram post ma\'lumotlarini tekshiradi (PHP bot asosida)',
        'endpoints': {
            'POST /check': {
                'description': 'Video tekshirish',
                'parameters': {
                    'url': 'Instagram post URL',
                    'video_url': 'Instagram video URL', 
                    'target_text': 'Qidirilayotgan matn (ixtiyoriy)'
                }
            },
            'GET /post-info': {
                'description': 'Post ma\'lumotlarini olish'
            }
        },
        'default_target_text': 'RekchiAi_bot'
    })

@app.route('/check', methods=['POST'])
def check_video():
    """Instagram video tekshirish"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'approved': False,
                'error': 'JSON ma\'lumotlari talab qilinadi'
            }), 400
        
        # URL ni olish
        url = data.get('url') or data.get('video_url') or data.get('instagram_url')
        target_text = data.get('target_text', 'RekchiAi_bot')
        
        if not url:
            return jsonify({
                'success': False,
                'approved': False,
                'error': 'URL maydoni talab qilinadi'
            }), 400
        
        logger.info(f"🎬 Tekshirish so'rovi: {url}")
        logger.info(f"🎯 Qidirilayotgan matn: {target_text}")
        
        # Instagram post ma'lumotlarini olish
        post_data = get_instagram_post_data(url)
        
        if not post_data:
            return jsonify({
                'success': False,
                'approved': False,
                'error': 'Instagram post ma\'lumotlari olinmadi'
            }), 404
        
        # Matnni tekshirish
        has_target_text = check_required_text(post_data, target_text)
        
        response_data = {
            'success': True,
            'approved': has_target_text,
            'found': has_target_text,
            'target_text': target_text,
            'post_data': {
                'has_caption': bool(post_data.get('caption')),
                'has_media': bool(post_data.get('media')),
                'data_keys': list(post_data.keys())
            },
            'message': 'Matn topildi - video qabul qilindi' if has_target_text else 'Matn topilmadi - video rad etildi'
        }
        
        logger.info(f"🎯 Yakuniy natija: {has_target_text}")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"❌ Server xatosi: {e}")
        return jsonify({
            'success': False,
            'approved': False,
            'error': f'Server xatosi: {str(e)}'
        }), 500

@app.route('/post-info', methods=['POST'])
def get_post_info():
    """Instagram post to'liq ma'lumotlarini olish"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON ma\'lumotlari talab qilinadi'
            }), 400
        
        url = data.get('url') or data.get('video_url')
        
        if not url:
            return jsonify({
                'success': False,
                'error': 'URL maydoni talab qilinadi'
            }), 400
        
        # Instagram post ma'lumotlarini olish
        post_data = get_instagram_post_data(url)
        
        if not post_data:
            return jsonify({
                'success': False,
                'error': 'Post ma\'lumotlari olinmadi'
            }), 404
        
        return jsonify({
            'success': True,
            'post_data': post_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server xatosi: {str(e)}'
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Server holati"""
    return jsonify({
        'status': 'ok',
        'service': 'Instagram Video Checker',
        'version': '3.0',
        'api_provider': 'insta.savetube.me'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    
    print("=" * 60)
    print("Instagram Video Checker API - PHP BOT VERSION")
    print("=" * 60)
    print(f"🚀 Server http://localhost:{port} da ishga tushmoqda...")
    print("\n📋 Endpoint'lar:")
    print("  POST /check      - Video tekshirish")
    print("  POST /post-info  - Post ma'lumotlarini olish")
    print("  GET  /health     - Server holati")
    print("\n🔧 API Provider: insta.savetube.me")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False)
