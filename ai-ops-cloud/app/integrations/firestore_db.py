"""Firestore Database Integration"""
from google.cloud import firestore
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class FirestoreDB:
    """Firestore database operations"""

    def __init__(self, project_id: str):
        self.db = firestore.Client(project=project_id)

    # CONTENT MANAGEMENT

    def save_content_day(self, day_number: int, data: dict):
        """
        Save content data for a specific day

        Args:
            day_number: Day number (1-30)
            data: Content data dictionary
        """
        doc_ref = self.db.collection('content_days').document(f'day_{day_number}')

        content_data = {
            'day_number': day_number,
            'status': data.get('status', 'prep'),
            'vision': data.get('vision', {}),
            'brief': data.get('brief', {}),
            'videos': data.get('videos', {}),
            'captions': data.get('captions', {}),
            'review': data.get('review', {}),
            'notion_page_id': data.get('notion_page_id', ''),
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }

        doc_ref.set(content_data, merge=True)
        logger.info(f"Saved content for Day {day_number}")

    def get_content_day(self, day_number: int) -> Optional[dict]:
        """
        Get content data for a specific day

        Args:
            day_number: Day number (1-30)

        Returns:
            Content data or None
        """
        doc_ref = self.db.collection('content_days').document(f'day_{day_number}')
        doc = doc_ref.get()

        if doc.exists:
            return doc.to_dict()
        return None

    def update_content_status(self, day_number: int, status: str):
        """
        Update status for a day's content

        Args:
            day_number: Day number
            status: prep|recording|review|approved|published
        """
        doc_ref = self.db.collection('content_days').document(f'day_{day_number}')
        doc_ref.update({
            'status': status,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        logger.info(f"Updated Day {day_number} status to: {status}")

    # METRICS MANAGEMENT

    def save_platform_metrics(self, day_number: int, platform: str, metrics: dict):
        """
        Save metrics for a platform

        Args:
            day_number: Day number
            platform: linkedin|facebook|instagram|twitter
            metrics: Metrics dictionary
        """
        doc_ref = self.db.collection('metrics').document(f'day_{day_number}')

        doc_ref.set({
            platform: {
                'impressions': metrics.get('impressions', 0),
                'engagement': metrics.get('engagement', 0),
                'comments': metrics.get('comments', 0),
                'shares': metrics.get('shares', 0),
                'updated_at': firestore.SERVER_TIMESTAMP
            }
        }, merge=True)

        logger.info(f"Saved {platform} metrics for Day {day_number}")

    def get_yesterday_metrics(self, day_number: int) -> dict:
        """
        Get metrics from previous day

        Args:
            day_number: Current day number

        Returns:
            Dictionary with all platform metrics
        """
        if day_number <= 1:
            # First day, return defaults
            return {
                'linkedin': {'impressions': 0, 'engagement': 0},
                'facebook': {'impressions': 0, 'engagement': 0},
                'instagram': {'impressions': 0, 'engagement': 0},
                'twitter': {'impressions': 0, 'engagement': 0}
            }

        doc_ref = self.db.collection('metrics').document(f'day_{day_number - 1}')
        doc = doc_ref.get()

        if doc.exists:
            return doc.to_dict()
        return {}

    # ENGAGEMENT MANAGEMENT

    def log_engagement(self, day_number: int, platform: str, engagement_data: dict):
        """
        Log an engagement (comment, like, etc.)

        Args:
            day_number: Day number
            platform: Platform name
            engagement_data: Engagement details
        """
        collection_ref = self.db.collection('engagement')

        doc_data = {
            'day_number': day_number,
            'platform': platform,
            'type': engagement_data.get('type', 'comment'),
            'author': engagement_data.get('author', ''),
            'content': engagement_data.get('content', ''),
            'priority': engagement_data.get('priority', 'low'),
            'action_taken': engagement_data.get('action_taken', 'pending'),
            'timestamp': firestore.SERVER_TIMESTAMP
        }

        collection_ref.add(doc_data)
        logger.info(f"Logged {platform} engagement for Day {day_number}")

    def get_priority_engagement(self, day_number: int) -> List[dict]:
        """
        Get high-priority engagement items

        Args:
            day_number: Day number

        Returns:
            List of high-priority engagement items
        """
        collection_ref = self.db.collection('engagement')

        query = collection_ref.where('day_number', '==', day_number) \
                              .where('priority', '==', 'high') \
                              .where('action_taken', '==', 'pending') \
                              .limit(20)

        docs = query.stream()
        return [doc.to_dict() for doc in docs]
