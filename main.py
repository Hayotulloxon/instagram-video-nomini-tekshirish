from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import logging

app = FastAPI(title="Instagram Video Check API", version="1.0.0")

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic modellari
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
        if 'instagram.com/p/' in url:
            # Post uchun
            post_id = url.split('/p/')[1].split('/')[0]
            return {
                'success': True,
                'title': f'Instagram post {post_id}',
                'description': 'Instagram video content'
            }
        elif 'instagram.com/reel/' in url:
            # Reel uchun
            reel_id = url.split('/reel/')[1].split('/')[0]
            return {
                'success': True,
                'title': f'Instagram Reel {reel_id}',
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

@app.post("/check")
async def check_video_text(request: VideoCheckRequest):
    """
    Video havolasida kerakli hashtag borligini tekshirish
    """
    try:
        logger.info(f"Video tekshirish so'rovi: {request.video_url}")
        
        # YANGI: Hashtag formatida kerakli matn
        REQUIRED_HASHTAGS = [
            "#Videolaringizni rekga chiqaradigan suniy intelektni hohlaysizmi? Telegramga RekchiAi_bot ga kiring.",
            "#Telegramdagi", 
            "#RekchiAi_bot"
        ]
        
        # Instagram video ma'lumotlarini olish
        video_info = extract_instagram_video_info(request.video_url)
        
        if not video_info['success']:
            return VideoCheckResponse(
                success=False,
                has_text=False,
                error=video_info.get('error', 'Video ma\'lumotlarini olishda xatolik')
            )
        
        # Kontentni yig'amiz (simulyatsiya)
        content = ""
        if video_info.get('title'):
            content += video_info['title'] + " "
        if video_info.get('description'):
            content += video_info['description'] + " "
        
        # BARCHA hashtag larni tekshiramiz
        all_hashtags_found = all(check_text_in_content(content, hashtag) for hashtag in REQUIRED_HASHTAGS)
        
        return VideoCheckResponse(
            success=True,
            has_text=all_hashtags_found,
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

@app.post("/check_hashtag")
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
            "POST /check": "Video hashtaglarini tekshirish",
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
