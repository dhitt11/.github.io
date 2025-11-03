"""Multi-Platform Publishing Workflow"""
import logging
from typing import Dict
from app.integrations.linkedin_api import LinkedInPublisher
from app.integrations.facebook_api import FacebookPublisher
from app.integrations.instagram_api import InstagramPublisher
from app.integrations.twitter_api import TwitterPublisher
from app.integrations.firestore_db import FirestoreDB
from app.integrations.notion_api import NotionClient
from app.integrations.slack_api import SlackNotifier
from app.config import get_settings

logger = logging.getLogger(__name__)

class MultiPlatformPublisher:
    """Publish to all platforms simultaneously"""

    def __init__(self):
        settings = get_settings()

        # Initialize platform publishers
        self.linkedin = LinkedInPublisher(settings.linkedin_access_token)
        self.facebook = FacebookPublisher(
            settings.facebook_access_token,
            settings.facebook_page_id
        )
        self.instagram = InstagramPublisher(
            settings.instagram_access_token,
            settings.instagram_account_id
        )
        self.twitter = TwitterPublisher(
            settings.twitter_api_key,
            settings.twitter_api_secret,
            settings.twitter_access_token,
            settings.twitter_access_secret
        )

        # Initialize utilities
        self.db = FirestoreDB(settings.google_cloud_project)
        self.notion = NotionClient()
        self.slack = SlackNotifier(settings.slack_webhook_url)

    def publish_day(self, day_number: int) -> Dict[str, dict]:
        """
        Publish content for a day to all platforms

        Args:
            day_number: Day number to publish

        Returns:
            Results dictionary with success/failure per platform
        """
        logger.info(f"Publishing Day {day_number} to all platforms")

        # Get content from Firestore
        content_data = self.db.get_content_day(day_number)

        if not content_data:
            logger.error(f"No content found for Day {day_number}")
            return {}

        videos = content_data.get('videos', {})
        captions = content_data.get('captions', {})

        results = {}

        # LINKEDIN (Primary)
        logger.info("Publishing to LinkedIn...")
        results['linkedin'] = self.linkedin.post_video(
            video_url=videos.get('linkedin', ''),
            caption=captions.get('linkedin_caption', '')
        )

        # FACEBOOK
        logger.info("Publishing to Facebook...")
        results['facebook'] = self.facebook.post_video(
            video_url=videos.get('facebook', ''),
            caption=captions.get('facebook_caption', '')
        )

        # INSTAGRAM
        logger.info("Publishing to Instagram...")
        results['instagram'] = self.instagram.post_reel(
            video_url=videos.get('instagram', ''),
            caption=captions.get('instagram_caption', '')
        )

        # TWITTER
        logger.info("Publishing to Twitter...")
        results['twitter'] = self.twitter.post_thread(
            tweets=captions.get('twitter_thread', []),
            video_url=videos.get('twitter', '')
        )

        # Update status
        self.db.update_content_status(day_number, 'published')

        # Update Notion
        if 'notion_page_id' in content_data:
            self.notion.update_review_card(
                content_data['notion_page_id'],
                {'status': 'Published'}
            )

        # Send Slack summary
        self._send_publish_summary(day_number, results)

        logger.info(f"Publishing completed for Day {day_number}")
        return results

    def _send_publish_summary(self, day_number: int, results: dict):
        """Send Slack notification with publish results"""
        message = f"🚀 Day {day_number} Published!\n\n"

        for platform, result in results.items():
            if result.get('success'):
                emoji = '✅'
                status = "Live!"
            else:
                emoji = '❌'
                status = f"Failed: {result.get('error', 'Unknown error')}"

            message += f"{emoji} {platform.upper()}: {status}\n"

        self.slack.send_message(message)
