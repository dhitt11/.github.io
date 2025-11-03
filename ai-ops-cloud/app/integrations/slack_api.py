"""Slack API Integration"""
import requests
import logging

logger = logging.getLogger(__name__)

class SlackNotifier:
    """Simple Slack notifications via webhook"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_message(self, text: str):
        """
        Send message to Slack

        Args:
            text: Message text
        """
        payload = {"text": text}

        try:
            response = requests.post(self.webhook_url, json=payload)
            if response.status_code == 200:
                logger.info("Slack notification sent")
            else:
                logger.error(f"Slack notification failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Slack notification error: {str(e)}")
