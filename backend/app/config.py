from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
from typing import List
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load .env file from the backend directory
_backend_dir = Path(__file__).parent.parent
_env_file = _backend_dir / ".env"
load_dotenv(_env_file, override=True)


class Settings(BaseSettings):
    # Meta Ads
    meta_ad_account_id: str = ""
    meta_access_token: str = Field(default="", description="Meta Graph API Access Token")

    # MCP Gateway
    gateway_url: str = Field(default="https://gatewayapi-production.up.railway.app", description="MCP Gateway URL")
    gateway_token: str = Field(default="", description="MCP Gateway Bearer Token")

    # Google Ads
    google_ads_developer_token: str = Field(default="", description="Google Ads API Developer Token")
    google_ads_client_id: str = Field(default="", description="Google OAuth2 Client ID")
    google_ads_client_secret: str = Field(default="", description="Google OAuth2 Client Secret")
    google_ads_refresh_token: str = Field(default="", description="Google OAuth2 Refresh Token")
    google_ads_customer_id: str = Field(default="3428920141", description="Google Ads Customer ID")
    google_ads_manager_id: str = Field(default="5405350977", description="Google Ads MCC Manager ID")

    # Claude API
    anthropic_api_key: str = ""

    # Slack Webhook (for notifications)
    slack_webhook_url: str = ""

    # Slack Bot (JARVIS) Configuration
    slack_bot_token: str = Field(default="", description="Slack Bot OAuth Token (xoxb-...)")
    slack_signing_secret: str = Field(default="", description="Slack Signing Secret")
    slack_app_token: str = Field(default="", description="Slack App-Level Token for Socket Mode (xapp-...)")

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/dashboard.db"

    # App Settings
    audit_interval_hours: int = 4
    spend_anomaly_threshold: float = 0.5
    log_level: str = Field(default="info", description="Logging level")

    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]

    # Feature flags
    enable_slack_bot: bool = Field(default=True, description="Enable JARVIS Slack bot")

    model_config = SettingsConfigDict(
        env_file=str(_env_file),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def is_slack_bot_configured(self) -> bool:
        """Check if Slack bot credentials are properly configured."""
        return bool(
            self.slack_bot_token
            and self.slack_signing_secret
            and self.slack_app_token
            and self.slack_bot_token.startswith("xoxb-")
            and self.slack_app_token.startswith("xapp-")
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
