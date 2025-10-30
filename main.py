from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import logging
import re

app = Flask(__name__)

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_instagram_content(url: str):
    """
    Instagram post dan haqiqiy kontentni olish
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Meta description ni olish
        description = soup.find('meta', attrs={'property': 'og:description'})
        description_text = description.get('content', '') if description else ''
        
        # Title ni olish
        title = soup.find('title')
        title_text = title.get_text() if title else ''
        
        # Barcha matn kontentini olish
        all_text = soup.get_text()
        
        return {
            'success': True,
            'title': title_text,
            'description': description_text,
            'full_content': all_text,
            'content': title_text + " " + description_text + " " + all_text
        }
        
    except Exception as e:
        logger.error(f"Instagram content extract error: {str(e)}")
        return {
            'success': False,
            'error': f'Kontent olishda xatolik: {str(e)}'
        }

def check_text_in_content(content: str, required_text: str) -> bool:
    """
    Kontentda kerakli matn borligini tekshirish
    """
    try:
        content_lower = content.lower().strip()
        required_lower = required_text.lower().strip()
        
        # Debug uchun
        logger.info(f"Tekshirilayotgan matn: {required_lower}")
        logger.info(f"Kontentda bor: {required_lower in content_lower}")
        
        return required_lower in content_lower
        
    except Exception as e:
        logger.error(f"Text check error: {str(e)}")
        return False

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
        
        # Hashtag formatida kerakli matn
        REQUIRED_HASHTAGS = [
            "#Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring.",
            "#Telegramdagi", 
            "#RekchiAi_bot"
        ]
        
        # Haqiqiy Instagram kontentini olish
        content_info = extract_instagram_content(video_url)
        
        if not content_info['success']:
            return jsonify({
                'success': False,
                'has_text': False,
                'error': content_info.get('error', 'Kontent olishda xatolik')
            }), 400
        
        # Kontentni olish
        content = content_info.get('content', '')
        
        # Debug ma'lumotlari
        logger.info(f"Topilgan kontent uzunligi: {len(content)}")
        logger.info(f"Kontent namunasi: {content[:200]}...")
        
        # BARCHA hashtag larni tekshiramiz
        found_hashtags = []
        for hashtag in REQUIRED_HASHTAGS:
            found = check_text_in_content(content, hashtag)
            found_hashtags.append({
                'hashtag': hashtag,
                'found': found
            })
        
        all_hashtags_found = all(item['found'] for item in found_hashtags)
        
        return jsonify({
            'success': True,
            'has_text': all_hashtags_found,
            'title': content_info.get('title', 'Instagram video'),
            'found_hashtags': found_hashtags,  # Qaysi hashtag lar topilganligi
            'content_preview': content[:500] if len(content) > 500 else content,  # Debug uchun
            'error': None
        })
        
    except Exception as e:
        logger.error(f"Video check error: {str(e)}")
        return jsonify({
            'success': False,
            'has_text': False,
            'error': f"Server xatosi: {str(e)}"
        }), 500

@app.route('/')
def root():
    """Asosiy sahifa"""
    return jsonify({
        "message": "Instagram Video Check API",
        "version": "2.0.0",
        "endpoints": {
            "POST /check": "Video hashtaglarini tekshirish (haqiqiy kontent)"
        }
    })

@app.route('/health')
def health_check():
    """Sog'lik tekshiruvi"""
    return jsonify({"status": "healthy", "service": "Instagram Video Check API"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
