"""Notion API Integration"""
import requests
import logging
from typing import Dict, List
from app.config import get_settings

logger = logging.getLogger(__name__)

class NotionClient:
    """Notion API operations"""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.notion_api_key
        self.database_id = settings.notion_database_id
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.base_url = "https://api.notion.com/v1"

    def create_review_card(self, day_number: int, content_data: dict) -> str:
        """
        Create a new review card in Notion database

        Args:
            day_number: Day number
            content_data: All content data

        Returns:
            Page ID of created card
        """
        url = f"{self.base_url}/pages"

        # Build properties
        properties = {
            "Day": {"number": day_number},
            "Status": {
                "select": {"name": content_data.get('status', 'Review')}
            },
            "LinkedIn Video": {
                "url": content_data.get('videos', {}).get('linkedin', '')
            },
            "Facebook Video": {
                "url": content_data.get('videos', {}).get('facebook', '')
            },
            "Instagram Video": {
                "url": content_data.get('videos', {}).get('instagram', '')
            },
            "Twitter Video": {
                "url": content_data.get('videos', {}).get('twitter', '')
            }
        }

        # Add captions as rich text
        for platform in ['linkedin', 'facebook', 'instagram']:
            caption = content_data.get('captions', {}).get(f'{platform}_caption', '')
            if caption:
                properties[f"{platform.capitalize()} Caption"] = {
                    "rich_text": [{"text": {"content": caption[:2000]}}]  # Notion limit
                }

        # Twitter thread (join tweets)
        twitter_thread = content_data.get('captions', {}).get('twitter_thread', [])
        if twitter_thread:
            thread_text = '\n\n'.join(twitter_thread)
            properties["Twitter Thread"] = {
                "rich_text": [{"text": {"content": thread_text[:2000]}}]
            }

        payload = {
            "parent": {"database_id": self.database_id},
            "properties": properties
        }

        response = requests.post(url, headers=self.headers, json=payload)

        if response.status_code == 200:
            page_id = response.json()['id']
            logger.info(f"Created Notion card for Day {day_number}: {page_id}")
            return page_id
        else:
            logger.error(f"Failed to create Notion card: {response.text}")
            raise Exception(f"Notion API error: {response.status_code}")

    def update_review_card(self, page_id: str, updates: dict):
        """
        Update an existing Notion page

        Args:
            page_id: Notion page ID
            updates: Properties to update
        """
        url = f"{self.base_url}/pages/{page_id}"

        properties = {}

        # Handle status update
        if 'status' in updates:
            properties["Status"] = {
                "select": {"name": updates['status']}
            }

        # Handle metrics
        if 'total_reach' in updates:
            properties["Total Reach"] = {"number": updates['total_reach']}

        if 'total_engagement' in updates:
            properties["Total Engagement"] = {"number": updates['total_engagement']}

        payload = {"properties": properties}

        response = requests.patch(url, headers=self.headers, json=payload)

        if response.status_code == 200:
            logger.info(f"Updated Notion card: {page_id}")
        else:
            logger.error(f"Failed to update Notion card: {response.text}")

    def get_approved_cards(self) -> List[dict]:
        """
        Get all cards with status = 'Approved'

        Returns:
            List of approved card data
        """
        url = f"{self.base_url}/databases/{self.database_id}/query"

        payload = {
            "filter": {
                "property": "Status",
                "select": {
                    "equals": "Approved"
                }
            }
        }

        response = requests.post(url, headers=self.headers, json=payload)

        if response.status_code == 200:
            results = response.json()['results']
            logger.info(f"Found {len(results)} approved cards")
            return results
        else:
            logger.error(f"Failed to query Notion: {response.text}")
            return []

    def add_comment_to_page(self, page_id: str, comment: str):
        """
        Add a comment to a Notion page

        Args:
            page_id: Notion page ID
            comment: Comment text
        """
        url = f"{self.base_url}/comments"

        payload = {
            "parent": {"page_id": page_id},
            "rich_text": [{"text": {"content": comment}}]
        }

        response = requests.post(url, headers=self.headers, json=payload)

        if response.status_code == 200:
            logger.info(f"Added comment to page: {page_id}")
        else:
            logger.error(f"Failed to add comment: {response.text}")
