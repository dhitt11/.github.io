"""Base agent class for AI Operations"""
import logging
from abc import ABC, abstractmethod
from anthropic import Anthropic
from app.config import get_settings

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all AI agents"""

    def __init__(self):
        self.settings = get_settings()
        self.client = Anthropic(api_key=self.settings.anthropic_api_key)
        self.model = "claude-sonnet-4.5-20250929"

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent"""
        pass

    async def execute(self, user_message: str, context: dict = None) -> str:
        """Execute the agent with given message and context"""
        try:
            logger.info(f"{self.__class__.__name__} executing with message: {user_message[:100]}...")

            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.get_system_prompt(),
                messages=[{"role": "user", "content": user_message}]
            )

            response = message.content[0].text
            logger.info(f"{self.__class__.__name__} completed successfully")
            return response

        except Exception as e:
            logger.error(f"{self.__class__.__name__} failed: {str(e)}")
            raise
