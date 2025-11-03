"""Visionary Agent - Strategic content planning"""
from app.agents.base_agent import BaseAgent
import json
from pathlib import Path

class VisionaryAgent(BaseAgent):
    """Strategic planning and content direction"""

    def __init__(self):
        prompt_path = Path("config/prompts/visionary.txt")
        system_prompt = prompt_path.read_text()
        super().__init__(role="visionary", system_prompt=system_prompt)

    def analyze_and_recommend(self, metrics: dict) -> dict:
        """
        Analyze platform metrics and recommend content

        Args:
            metrics: Dictionary with performance data from all platforms

        Returns:
            Dictionary with content recommendations
        """
        user_message = f"""
        Here are yesterday's metrics across all platforms:

        {json.dumps(metrics, indent=2)}

        Based on this data, provide today's content recommendation.
        Remember to respond ONLY with valid JSON in the format specified.
        """

        response = self.invoke(user_message, max_tokens=2000)

        # Parse JSON response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse Visionary response as JSON")
            # Return default structure
            return {
                "recommended_topic": "Building automated systems with AI",
                "reasoning": "Core competency, always performs well",
                "platform_adaptations": {},
                "engagement_prediction": {},
                "business_impact": "Demonstrates expertise",
                "effort_level": "medium"
            }
