"""
Google OAuth2 service for Google Slides, Docs, and Drive write access.

Handles the OAuth2 flow and token management for creating
Google Slides presentations and Google Docs documents.
"""

import json
import structlog
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request

logger = structlog.get_logger(__name__)

# Scopes needed for creating Slides and Docs
SCOPES = [
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

# Token storage path
TOKEN_PATH = Path(__file__).parent.parent.parent / "data" / "google_token.json"


class GoogleAuthService:
    """Manages Google OAuth2 credentials for Slides/Docs API access."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://localhost:8001/api/auth/google/callback",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._credentials: Optional[Credentials] = None

        # Try to load existing token
        self._load_token()

    @property
    def is_configured(self) -> bool:
        """Check if OAuth credentials are configured."""
        return bool(self.client_id and self.client_secret)

    @property
    def is_authenticated(self) -> bool:
        """Check if we have valid credentials."""
        if self._credentials is None:
            return False
        if self._credentials.expired and self._credentials.refresh_token:
            try:
                self._credentials.refresh(Request())
                self._save_token()
                return True
            except Exception as e:
                logger.error("google_token_refresh_failed", error=str(e))
                return False
        return self._credentials.valid

    def get_credentials(self) -> Optional[Credentials]:
        """Get valid Google credentials, refreshing if needed."""
        if self._credentials is None:
            return None
        if self._credentials.expired and self._credentials.refresh_token:
            try:
                self._credentials.refresh(Request())
                self._save_token()
            except Exception as e:
                logger.error("google_token_refresh_failed", error=str(e))
                return None
        return self._credentials

    def get_auth_url(self) -> str:
        """Generate the OAuth2 authorization URL."""
        flow = self._create_flow()
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return auth_url

    def handle_callback(self, authorization_response: str) -> bool:
        """Handle the OAuth2 callback and store credentials."""
        try:
            flow = self._create_flow()
            flow.fetch_token(authorization_response=authorization_response)
            self._credentials = flow.credentials
            self._save_token()
            logger.info("google_oauth_success")
            return True
        except Exception as e:
            logger.error("google_oauth_callback_failed", error=str(e))
            return False

    def disconnect(self) -> None:
        """Remove stored credentials."""
        self._credentials = None
        if TOKEN_PATH.exists():
            TOKEN_PATH.unlink()
        logger.info("google_oauth_disconnected")

    def _create_flow(self) -> Flow:
        """Create an OAuth2 flow instance."""
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri],
            }
        }
        flow = Flow.from_client_config(client_config, scopes=SCOPES)
        flow.redirect_uri = self.redirect_uri
        return flow

    def _load_token(self) -> None:
        """Load saved token from disk."""
        if TOKEN_PATH.exists():
            try:
                with open(TOKEN_PATH, "r") as f:
                    token_data = json.load(f)
                self._credentials = Credentials.from_authorized_user_info(
                    token_data, SCOPES
                )
                logger.info("google_token_loaded")
            except Exception as e:
                logger.warning("google_token_load_failed", error=str(e))

    def _save_token(self) -> None:
        """Save credentials to disk."""
        if self._credentials:
            TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(TOKEN_PATH, "w") as f:
                json.dump(json.loads(self._credentials.to_json()), f, indent=2)
            logger.info("google_token_saved")
