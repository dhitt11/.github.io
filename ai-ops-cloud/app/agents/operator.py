"""Operator Agent - Workflow coordination"""
from app.agents.base_agent import BaseAgent
import json
from pathlib import Path

class OperatorAgent(BaseAgent):
    """Coordination and process management"""

    def __init__(self):
        prompt_path = Path("config/prompts/operator.txt")
        system_prompt = prompt_path.read_text()
        super().__init__(role="operator", system_prompt=system_prompt)

    def create_clear_picture(self, vision: dict) -> dict:
        """
        Create Clear Picture brief from Visionary's recommendation

        Args:
            vision: Visionary's content recommendation

        Returns:
            Clear Picture brief as dictionary
        """
        user_message = f"""
        Create a Clear Picture brief based on this strategic recommendation:

        {json.dumps(vision, indent=2)}

        Provide the brief in the JSON format specified.
        """

        response = self.invoke(user_message, max_tokens=2000)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse Operator response as JSON")
            return {"objective": "Create content", "core_message": vision.get("recommended_topic", "")}

    def triage_engagement(self, engagement_item: dict, platform: str) -> dict:
        """
        Triage an engagement item (comment, message, etc.)

        Args:
            engagement_item: The comment/message to triage
            platform: Which platform it's from

        Returns:
            Triage result with priority and action
        """
        user_message = f"""
        Triage this {platform} engagement:

        Author: {engagement_item.get('author', 'Unknown')}
        Content: {engagement_item.get('content', '')}

        Respond with JSON:
        {{
          "priority": "high|medium|low",
          "action": "flag_human|auto_respond|ignore",
          "reason": "Brief explanation",
          "suggested_response": "If auto-respond, the response text"
        }}
        """

        response = self.invoke(user_message, max_tokens=500)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "priority": "medium",
                "action": "flag_human",
                "reason": "Couldn't parse, better safe than sorry"
            }
