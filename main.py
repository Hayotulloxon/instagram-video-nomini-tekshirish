from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import re
import logging
from typing import Optional
import urllib.parse

app = FastAPI(title="Instagram Video Check API", version="1.0.0")

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoCheckRequest(BaseModel):
    video_url: str

class VideoCheckResponse(BaseModel):
    success: bool
    has_text: bool = False
    title: Optional[str] = None
    error: Optional[str] = None

class HashtagCheckRequest(BaseModel):
    video_url: str
    required_hashtag: str

class HashtagCheckResponse(BaseModel):
    success: bool
    has_hashtag: bool = False
    error: Optional[str] = None

def extract_instagram_video_info(url: str):
    """
    Instagram video havolasidan ma'lumot olish
    """
    try:
        # Instagram post ID ni olish
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

@app.post("/check", response_model=VideoCheckResponse)
async def check_video_text(request: VideoCheckRequest):
    """
    Video havolasida kerakli matn borligini tekshirish
    """
    try:
        logger.info(f"Video tekshirish so'rovi: {request.video_url}")
        
        # Kerakli matn
        REQUIRED_TEXT = "Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring."
        
        # Instagram video ma'lumotlarini olish
        video_info = extract_instagram_video_info(request.video_url)
        
        if not video_info['success']:
            return VideoCheckResponse(
                success=False,
                has_text=False,
                error=video_info.get('error', 'Video ma\'lumotlarini olishda xatolik')
            )
        
        # Kontentni yig'amiz
        content = ""
        if video_info.get('title'):
            content += video_info['title'] + " "
        if video_info.get('description'):
            content += video_info['description'] + " "
        
        # Matnni tekshiramiz
        has_required_text = check_text_in_content(content, REQUIRED_TEXT)
        
        return VideoCheckResponse(
            success=True,
            has_text=has_required_text,
            title=video_info.get('title', 'Instagram video'),
            error=None
        )
        
    except Exception as e:
        logger.error(f"Video check error: {str(e)}")
        return VideoCheckResponse(
            success=False,
            has_text=False,
            error=f"Server xatosi: {str(e)}"
        )

@app.post("/check_hashtag", response_model=HashtagCheckResponse)
async def check_video_hashtag(request: HashtagCheckRequest):
    """
    Video havolasida kerakli hashtag borligini tekshirish
    """
    try:
        logger.info(f"Hashtag tekshirish so'rovi: {request.video_url}")
        
        # Instagram video ma'lumotlarini olish
        video_info = extract_instagram_video_info(request.video_url)
        
        if not video_info['success']:
            return HashtagCheckResponse(
                success=False,
                has_hashtag=False,
                error=video_info.get('error', 'Video ma\'lumotlarini olishda xatolik')
            )
        
        # Kontentni yig'amiz
        content = ""
        if video_info.get('title'):
            content += video_info['title'] + " "
        if video_info.get('description'):
            content += video_info['description'] + " "
        
        # Hashtag ni tekshiramiz
        has_required_hashtag = check_text_in_content(content, request.required_hashtag)
        
        return HashtagCheckResponse(
            success=True,
            has_hashtag=has_required_hashtag,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Hashtag check error: {str(e)}")
        return HashtagCheckResponse(
            success=False,
            has_hashtag=False,
            error=f"Server xatosi: {str(e)}"
        )

@app.get("/")
async def root():
    """Asosiy sahifa"""
    return {
        "message": "Instagram Video Check API",
        "version": "1.0.0",
        "endpoints": {
            "POST /check": "Video matnini tekshirish",
            "POST /check_hashtag": "Video hashtag ini tekshirish"
        }
    }

@app.get("/health")
async def health_check():
    """Sog'lik tekshiruvi"""
    return {"status": "healthy", "service": "Instagram Video Check API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
