"""Implementer Agent - Content creation and execution"""
from app.agents.base_agent import BaseAgent
import json
from pathlib import Path

class ImplementerAgent(BaseAgent):
    """Execution and technical implementation"""

    def __init__(self):
        prompt_path = Path("config/prompts/implementer.txt")
        system_prompt = prompt_path.read_text()
        super().__init__(role="implementer", system_prompt=system_prompt)

    def generate_captions(self, brief: dict) -> dict:
        """
        Generate platform-specific captions from Clear Picture brief

        Args:
            brief: Clear Picture brief with core message

        Returns:
            Dictionary with captions for each platform
        """
        user_message = f"""
        Generate platform-specific captions based on this brief:

        Core Message: {brief.get('core_message', '')}
        Talking Points: {json.dumps(brief.get('talking_points', []))}

        Platform Versions:
        {json.dumps(brief.get('platform_versions', {}), indent=2)}

        Create captions following the rules for each platform.
        Respond ONLY with valid JSON in the format specified.
        """

        response = self.invoke(user_message, max_tokens=3000)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse Implementer response as JSON")
            # Return minimal structure
            return {
                "linkedin_caption": brief.get('core_message', ''),
                "facebook_caption": brief.get('core_message', ''),
                "instagram_caption": brief.get('core_message', ''),
                "twitter_thread": [brief.get('core_message', '')]
            }
