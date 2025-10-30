from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/')
def home():
    return "Instagram Video Title Checker API ishga tushdi!"

@app.route('/check_hashtag', methods=['POST'])
def check_hashtag():
    data = request.get_json()
    video_url = data.get('video_url', '')

    if not video_url:
        return jsonify({'success': False, 'error': 'video_url kiritilmadi'})

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(video_url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        title_tag = soup.find("meta", property="og:title")
        title = title_tag["content"] if title_tag else "nom topilmadi"

        target_text = "#Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring. #Telegramdagi #RekchiAi_bot"
        has_text = target_text in title

        return jsonify({
            'success': True,
            'video_title': title,
            'has_text': has_text
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
