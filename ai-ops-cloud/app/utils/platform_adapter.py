"""Platform-specific Content Adaptation"""
import logging

logger = logging.getLogger(__name__)

class PlatformAdapter:
    """Adapts content for different social media platforms"""

    def __init__(self):
        self.platform_limits = {
            "linkedin": {
                "max_text": 3000,
                "hashtag_limit": 3,
                "supports_video": True,
                "supports_carousel": True
            },
            "facebook": {
                "max_text": 63206,
                "hashtag_limit": 2,
                "supports_video": True,
                "supports_carousel": True
            },
            "instagram": {
                "max_text": 2200,
                "hashtag_limit": 30,
                "supports_video": True,
                "supports_carousel": True
            },
            "twitter": {
                "max_text": 280,
                "hashtag_limit": 2,
                "supports_video": True,
                "supports_carousel": False
            }
        }

    def adapt_content(self, content: str, platform: str) -> str:
        """Adapt content for specific platform"""
        logger.info(f"Adapting content for {platform}")

        limits = self.platform_limits.get(platform)
        if not limits:
            raise ValueError(f"Unknown platform: {platform}")

        # Truncate if needed
        if len(content) > limits["max_text"]:
            content = content[:limits["max_text"] - 3] + "..."

        return content

    def validate_hashtags(self, hashtags: list, platform: str) -> list:
        """Validate and limit hashtags for platform"""
        # Implementation will be added in next prompt
        pass

    def format_post(self, content: dict, platform: str) -> dict:
        """Format post according to platform requirements"""
        # Implementation will be added in next prompt
        pass
