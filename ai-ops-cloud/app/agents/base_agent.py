"""Base agent class for AI Operations"""
import logging
from anthropic import Anthropic
from app.config import get_settings

class BaseAgent:
    """Base class for all AI agents"""

    def __init__(self, role: str, system_prompt: str):
        self.role = role
        self.system_prompt = system_prompt
        self.settings = get_settings()
        self.client = Anthropic(api_key=self.settings.anthropic_api_key)
        self.logger = logging.getLogger(f"agent.{role}")

    def invoke(self, user_message: str, max_tokens: int = 4000) -> str:
        """
        Send message to Claude and get response

        Args:
            user_message: The prompt/question for the agent
            max_tokens: Maximum tokens in response

        Returns:
            Agent's response as string
        """
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=max_tokens,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            result = response.content[0].text
            self.logger.info(f"{self.role} agent invoked successfully")
            return result

        except Exception as e:
            self.logger.error(f"{self.role} agent error: {str(e)}")
            raise
