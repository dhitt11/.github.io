from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str

    # Google Cloud
    google_cloud_project: str
    gcs_bucket_raw: str
    gcs_bucket_processed: str

    # Notion
    notion_api_key: str
    notion_database_id: str

    # Social Media
    linkedin_access_token: str
    facebook_access_token: str
    facebook_page_id: str
    instagram_access_token: str
    instagram_account_id: str
    twitter_api_key: str
    twitter_api_secret: str
    twitter_access_token: str
    twitter_access_secret: str

    # Slack
    slack_webhook_url: str

    # Application
    environment: str = "development"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings():
    return Settings()
