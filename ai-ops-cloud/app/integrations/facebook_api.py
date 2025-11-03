"""Facebook API Integration"""
import requests
import logging

logger = logging.getLogger(__name__)

class FacebookPublisher:
    """Facebook Graph API for posting"""

    def __init__(self, access_token: str, page_id: str):
        self.access_token = access_token
        self.page_id = page_id

    def post_video(self, video_url: str, caption: str) -> dict:
        """
        Post video to Facebook page

        Args:
            video_url: Public URL of video
            caption: Post caption

        Returns:
            Post data with ID
        """
        url = f"https://graph.facebook.com/v18.0/{self.page_id}/videos"

        payload = {
            "file_url": video_url,
            "description": caption,
            "access_token": self.access_token
        }

        try:
            response = requests.post(url, data=payload)

            if response.status_code == 200:
                data = response.json()
                post_id = data.get('id', '')
                logger.info(f"Posted to Facebook: {post_id}")
                return {"success": True, "post_id": post_id}
            else:
                logger.error(f"Facebook post failed: {response.text}")
                return {"success": False, "error": response.text}

        except Exception as e:
            logger.error(f"Facebook API error: {str(e)}")
            return {"success": False, "error": str(e)}
