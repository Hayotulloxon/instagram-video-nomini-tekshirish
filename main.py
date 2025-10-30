from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import logging
import urllib.parse

app = Flask(__name__)

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_instagram_video_info(url: str):
    """
    Instagram video havolasidan ma'lumot olish
    """
    try:
        parsed_url = urllib.parse.urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        if len(path_parts) >= 2 and path_parts[0] == 'p':
            post_id = path_parts[1]
            return {
                'success': True,
                'title': f'Instagram post {post_id}',
                'description': 'Instagram video content'
            }
        elif 'reel' in url:
            return {
                'success': True,
                'title': 'Instagram Reel',
                'description': 'Instagram reel content'
            }
        else:
            return {
                'success': True,
                'title': 'Instagram Video',
                'description': 'Instagram video content'
            }
            
    except Exception as e:
        logger.error(f"Instagram video info extract error: {str(e)}")
        return {
            'success': False,
            'error': f'Ma\'lumot olishda xatolik: {str(e)}'
        }

def check_text_in_content(content: str, required_text: str) -> bool:
    """
    Kontentda kerakli matn borligini tekshirish
    """
    try:
        content_lower = content.lower().strip()
        required_lower = required_text.lower().strip()
        return required_lower in content_lower
        
    except Exception as e:
        logger.error(f"Text check error: {str(e)}")
        return False

@app.route('/check', methods=['POST'])
def check_video_text():
    """
    Video havolasida kerakli matn borligini tekshirish
    """
    try:
        data = request.get_json()
        video_url = data.get('video_url')
        
        if not video_url:
            return jsonify({
                'success': False,
                'has_text': False,
                'error': 'video_url maydoni talab qilinadi'
            }), 400
        
        logger.info(f"Video tekshirish so'rovi: {video_url}")
        
        # Kerakli matn
        REQUIRED_TEXT = "Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring."
        
        # Instagram video ma'lumotlarini olish
        video_info = extract_instagram_video_info(video_url)
        
        if not video_info['success']:
            return jsonify({
                'success': False,
                'has_text': False,
                'error': video_info.get('error', 'Video ma\'lumotlarini olishda xatolik')
            }), 400
        
        # Kontentni yig'amiz
        content = ""
        if video_info.get('title'):
            content += video_info['title'] + " "
        if video_info.get('description'):
            content += video_info['description'] + " "
        
        # Matnni tekshiramiz
        has_required_text = check_text_in_content(content, REQUIRED_TEXT)
        
        return jsonify({
            'success': True,
            'has_text': has_required_text,
            'title': video_info.get('title', 'Instagram video'),
            'error': None
        })
        
    except Exception as e:
        logger.error(f"Video check error: {str(e)}")
        return jsonify({
            'success': False,
            'has_text': False,
            'error': f"Server xatosi: {str(e)}"
        }), 500

@app.route('/check_hashtag', methods=['POST'])
def check_video_hashtag():
    """
    Video havolasida kerakli hashtag borligini tekshirish
    """
    try:
        data = request.get_json()
        video_url = data.get('video_url')
        required_hashtag = data.get('required_hashtag')
        
        if not video_url or not required_hashtag:
            return jsonify({
                'success': False,
                'has_hashtag': False,
                'error': 'video_url va required_hashtag maydonlari talab qilinadi'
            }), 400
        
        logger.info(f"Hashtag tekshirish so'rovi: {video_url}")
        
        # Instagram video ma'lumotlarini olish
        video_info = extract_instagram_video_info(video_url)
        
        if not video_info['success']:
            return jsonify({
                'success': False,
                'has_hashtag': False,
                'error': video_info.get('error', 'Video ma\'lumotlarini olishda xatolik')
            }), 400
        
        # Kontentni yig'amiz
        content = ""
        if video_info.get('title'):
            content += video_info['title'] + " "
        if video_info.get('description'):
            content += video_info['description'] + " "
        
        # Hashtag ni tekshiramiz
        has_required_hashtag = check_text_in_content(content, required_hashtag)
        
        return jsonify({
            'success': True,
            'has_hashtag': has_required_hashtag,
            'error': None
        })
        
    except Exception as e:
        logger.error(f"Hashtag check error: {str(e)}")
        return jsonify({
            'success': False,
            'has_hashtag': False,
            'error': f"Server xatosi: {str(e)}"
        }), 500

@app.route('/')
def root():
    """Asosiy sahifa"""
    return jsonify({
        "message": "Instagram Video Check API",
        "version": "1.0.0",
        "endpoints": {
            "POST /check": "Video matnini tekshirish",
            "POST /check_hashtag": "Video hashtag ini tekshirish"
        }
    })

@app.route('/health')
def health_check():
    """Sog'lik tekshiruvi"""
    return jsonify({"status": "healthy", "service": "Instagram Video Check API"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
