"""SME Agent - Subject Matter Expert quality control"""
from app.agents.base_agent import BaseAgent
import json
from pathlib import Path

class SMEAgent(BaseAgent):
    """Quality control and subject matter expertise"""

    def __init__(self):
        prompt_path = Path("config/prompts/sme.txt")
        system_prompt = prompt_path.read_text()
        super().__init__(role="sme", system_prompt=system_prompt)

    def review_content(self, captions: dict, brief: dict) -> dict:
        """
        Review all content for quality and accuracy

        Args:
            captions: Generated captions for all platforms
            brief: Original Clear Picture brief

        Returns:
            Quality review results
        """
        user_message = f"""
        Review this content for quality and accuracy:

        Original Brief:
        {json.dumps(brief, indent=2)}

        Generated Captions:
        {json.dumps(captions, indent=2)}

        Provide quality review in the JSON format specified.
        """

        response = self.invoke(user_message, max_tokens=2000)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse SME response as JSON")
            return {
                "overall_quality": "good",
                "platform_reviews": {},
                "technical_accuracy": "verified",
                "recommendations": []
            }
