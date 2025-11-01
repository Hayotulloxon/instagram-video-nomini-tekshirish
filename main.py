from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import json
import html
import logging
import os

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_caption_from_instagram(url):
    """Instagram postdan caption ni olish"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        logger.info(f"📡 Instagram post so'rovi: {url}")
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        
        s = BeautifulSoup(r.text, 'html.parser')
        
        # 1. Meta description orqali
        m = s.find('meta', {'property': 'og:description'})
        if m and m.get('content'):
            caption = html.unescape(m['content'])
            logger.info("✅ Meta description orqali caption topildi")
            return caption
        
        # 2. JSON-LD orqali
        scripts = s.find_all('script', type='application/ld+json')
        for sc in scripts:
            try:
                j = json.loads(sc.string)
                if isinstance(j, dict) and 'caption' in j:
                    caption = j['caption']
                    logger.info("✅ JSON-LD orqali caption topildi")
                    return caption
            except:
                continue
        
        # 3. Window sharedData orqali
        js = s.find('script', string=re.compile('window\\._sharedData'))
        if js:
            txt = js.string
            jtxt = re.search(r'window\._sharedData\s*=\s*(\{.*\});', txt)
            if jtxt:
                try:
                    jd = json.loads(jtxt.group(1))
                    ed = jd.get('entry_data', {})
                    postpage = ed.get('PostPage', [])
                    if postpage:
                        media = postpage[0].get('graphql', {}).get('shortcode_media', {})
                        edges = media.get('edge_media_to_caption', {}).get('edges', [])
                        if edges:
                            caption = edges[0]['node']['text']
                            logger.info("✅ SharedData orqali caption topildi")
                            return caption
                except Exception as e:
                    logger.warning(f"SharedData parse xatosi: {e}")
        
        # 4. Regex orqali
        t = re.search(r'\"caption\":\"(.*?)\"', r.text)
        if t:
            caption = html.unescape(t.group(1))
            logger.info("✅ Regex orqali caption topildi")
            return caption
        
        logger.warning("❌ Hech qanday usul bilan caption topilmadi")
        return ''
        
    except Exception as e:
        logger.error(f"❌ Xato: {e}")
        return ''

@app.route('/', methods=['GET'])
def home():
    """API haqida ma'lumot"""
    return jsonify({
        'service': 'Instagram Caption Checker API',
        'version': '2.0',
        'description': 'Instagram post caption ichidagi matnni tekshiradi',
        'endpoints': {
            'POST /check': {
                'description': 'Caption tekshirish',
                'parameters': {
                    'url': 'Instagram post URL',
                    'video_url': 'Instagram video URL (alternativ)',
                    'target_text': 'Qidirilayotgan matn'
                }
            }
        },
        'default_target_text': 'RekchiAi_bot'
    })

@app.route('/check', methods=['POST'])
def check_caption():
    """Caption ni tekshirish"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'approved': False,
                'error': 'JSON ma\'lumotlari talab qilinadi'
            }), 400
        
        # Ikkala parametrni qo'llab-quvvatlash
        url = data.get('url') or data.get('video_url')
        target_text = data.get('target_text', 'RekchiAi_bot')
        
        if not url:
            return jsonify({
                'success': False,
                'approved': False,
                'error': 'URL maydoni talab qilinadi (url yoki video_url)'
            }), 400
        
        logger.info(f"🎬 Tekshirish so'rovi: {url}")
        logger.info(f"🎯 Qidirilayotgan matn: {target_text}")
        
        # Caption ni olish
        caption = get_caption_from_instagram(url)
        
        if not caption:
            return jsonify({
                'success': False,
                'approved': False,
                'error': 'Caption topilmadi yoki post mavjud emas'
            }), 404
        
        # Matnni tekshirish
        has_target_text = target_text.lower() in caption.lower()
        
        response_data = {
            'success': True,
            'approved': has_target_text,
            'found': has_target_text,
            'target_text': target_text,
            'caption_preview': caption[:200] + '...' if len(caption) > 200 else caption,
            'caption_length': len(caption),
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

@app.route('/health', methods=['GET'])
def health():
    """Server holati"""
    return jsonify({
        'status': 'ok',
        'service': 'Instagram Caption Checker',
        'version': '2.0'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
