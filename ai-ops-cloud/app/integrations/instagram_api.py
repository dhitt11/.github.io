"""Instagram API Integration"""
import requests
import logging

logger = logging.getLogger(__name__)

class InstagramPublisher:
    """Instagram Graph API for Reels"""

    def __init__(self, access_token: str, account_id: str):
        self.access_token = access_token
        self.account_id = account_id

    def post_reel(self, video_url: str, caption: str) -> dict:
        """
        Post Reel to Instagram

        Args:
            video_url: Public URL of video
            caption: Post caption

        Returns:
            Post data with ID
        """
        # Step 1: Create media container
        url = f"https://graph.facebook.com/v18.0/{self.account_id}/media"

        payload = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": self.access_token
        }

        try:
            # Create container
            response = requests.post(url, data=payload)

            if response.status_code == 200:
                container_id = response.json()['id']

                # Step 2: Publish container
                publish_url = f"https://graph.facebook.com/v18.0/{self.account_id}/media_publish"
                publish_payload = {
                    "creation_id": container_id,
                    "access_token": self.access_token
                }

                publish_response = requests.post(publish_url, data=publish_payload)

                if publish_response.status_code == 200:
                    reel_id = publish_response.json()['id']
                    logger.info(f"Posted to Instagram: {reel_id}")
                    return {"success": True, "post_id": reel_id}
                else:
                    logger.error(f"Instagram publish failed: {publish_response.text}")
                    return {"success": False, "error": publish_response.text}
            else:
                logger.error(f"Instagram container creation failed: {response.text}")
                return {"success": False, "error": response.text}

        except Exception as e:
            logger.error(f"Instagram API error: {str(e)}")
            return {"success": False, "error": str(e)}
