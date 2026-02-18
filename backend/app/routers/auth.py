"""
Authentication router for Google OAuth2.

Handles the OAuth flow for granting the dashboard permission
to create Google Slides and Google Docs in the user's Drive.
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.services.google_auth import GoogleAuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])

settings = get_settings()

# Singleton auth service
google_auth = GoogleAuthService(
    client_id=settings.google_oauth_client_id,
    client_secret=settings.google_oauth_client_secret,
    redirect_uri=settings.google_oauth_redirect_uri,
)


def get_google_auth() -> GoogleAuthService:
    """Get the Google auth service instance."""
    return google_auth


@router.get("/google/status")
async def google_auth_status():
    """Check if Google OAuth is connected."""
    return {
        "configured": google_auth.is_configured,
        "connected": google_auth.is_authenticated,
    }


@router.get("/google/start")
async def google_auth_start():
    """Start the Google OAuth2 flow. Returns the authorization URL."""
    if not google_auth.is_configured:
        return {
            "error": "Google OAuth not configured. Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in .env"
        }
    auth_url = google_auth.get_auth_url()
    return {"auth_url": auth_url}


@router.get("/google/callback")
async def google_auth_callback(request: Request):
    """Handle the OAuth2 callback from Google."""
    # Reconstruct the full authorization response URL
    authorization_response = str(request.url)

    success = google_auth.handle_callback(authorization_response)
    if success:
        # Redirect back to the reporting page
        return RedirectResponse(url="http://localhost:3000/reporting?auth=success")
    else:
        return RedirectResponse(url="http://localhost:3000/reporting?auth=error")


@router.post("/google/disconnect")
async def google_auth_disconnect():
    """Disconnect Google OAuth."""
    google_auth.disconnect()
    return {"status": "disconnected"}
