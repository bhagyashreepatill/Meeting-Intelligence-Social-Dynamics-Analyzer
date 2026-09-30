"""Configuration module for Meeting Intelligence & Social Dynamics Analyzer."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    app_name: str = "Meeting Intelligence & Social Dynamics Analyzer"
    app_env: str = "development"
    debug: bool = True

    # Demo Mode: 100% offline functionality without external credentials
    demo_mode: bool = True

    # Database
    database_url: str = "sqlite:///./meetings.db"

    # LLM Abstraction Layer
    llm_provider: str = "demo"  # "demo", "openai"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"

    # Integrations
    slack_webhook_url: Optional[str] = None
    slack_bot_token: Optional[str] = None
    slack_default_channel: str = "#meeting-actions"

    jira_server_url: Optional[str] = None
    jira_api_token: Optional[str] = None
    jira_user_email: Optional[str] = None
    jira_project_key: str = "PROJ"

    trello_api_key: Optional[str] = None
    trello_token: Optional[str] = None
    trello_list_id: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
