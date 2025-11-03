"""Overnight Preparation Workflow"""
import logging
from app.agents.visionary import VisionaryAgent
from app.agents.operator import OperatorAgent
from app.agents.implementer import ImplementerAgent
from app.agents.sme import SMEAgent
from app.integrations.firestore_db import FirestoreDB
from app.integrations.notion_api import NotionClient
from app.integrations.slack_api import SlackNotifier
from app.config import get_settings

logger = logging.getLogger(__name__)

class OvernightPrepWorkflow:
    """Overnight preparation workflow - runs at 2 AM"""

    def __init__(self):
        settings = get_settings()
        self.db = FirestoreDB(settings.google_cloud_project)
        self.notion = NotionClient()
        self.slack = SlackNotifier(settings.slack_webhook_url)

        # Initialize agents
        self.visionary = VisionaryAgent()
        self.operator = OperatorAgent()
        self.implementer = ImplementerAgent()
        self.sme = SMEAgent()

    def run(self, day_number: int):
        """
        Run overnight preparation for given day

        Args:
            day_number: Which day to prep for (1-30)
        """
        logger.info(f"Starting overnight prep for Day {day_number}")

        try:
            # Step 1: Get yesterday's metrics
            metrics = self.db.get_yesterday_metrics(day_number)
            logger.info(f"Retrieved metrics: {metrics}")

            # Step 2: Visionary analyzes and recommends
            vision = self.visionary.analyze_and_recommend(metrics)
            logger.info(f"Vision created: {vision.get('recommended_topic', '')}")

            # Step 3: Operator creates Clear Picture brief
            brief = self.operator.create_clear_picture(vision)
            logger.info("Clear Picture brief created")

            # Step 4: Implementer generates captions
            captions = self.implementer.generate_captions(brief)
            logger.info("Captions generated for all platforms")

            # Step 5: SME reviews quality
            review = self.sme.review_content(captions, brief)
            logger.info(f"Quality review: {review.get('overall_quality', 'unknown')}")

            # Step 6: Save everything to Firestore
            self.db.save_content_day(day_number, {
                'status': 'prep',
                'vision': vision,
                'brief': brief,
                'captions': captions,
                'review': review
            })

            # Step 7: Notify via Slack
            self.slack.send_message(
                f"☕ Day {day_number} prep complete!\n\n"
                f"Topic: {vision.get('recommended_topic', 'Unknown')}\n"
                f"Quality: {review.get('overall_quality', 'Unknown')}\n\n"
                f"Ready for your video recording. Upload to Cloud Storage when ready."
            )

            logger.info(f"Overnight prep completed for Day {day_number}")
            return True

        except Exception as e:
            logger.error(f"Overnight prep failed: {str(e)}")
            self.slack.send_message(
                f"❌ Day {day_number} prep FAILED\n\nError: {str(e)}"
            )
            return False
