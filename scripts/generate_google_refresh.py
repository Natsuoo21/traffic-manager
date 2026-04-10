"""
Run Google OAuth2 desktop flow to generate a refresh token for Google Ads API.

Usage:
    1. Go to Google Cloud Console → Create OAuth2 Desktop credentials
    2. Set GOOGLE_ADS_CLIENT_ID and GOOGLE_ADS_CLIENT_SECRET in .env.development
    3. Run: python scripts/generate_google_refresh.py
    4. Authorize in the browser
    5. Copy the refresh token to .env.development GOOGLE_ADS_REFRESH_TOKEN
"""

import sys


def main() -> None:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Install google-auth-oauthlib: pip install google-auth-oauthlib")
        sys.exit(1)

    # Try loading from .env
    try:
        from dotenv import dotenv_values
        env = dotenv_values("backend/.env.development")
        client_id = env.get("GOOGLE_ADS_CLIENT_ID", "")
        client_secret = env.get("GOOGLE_ADS_CLIENT_SECRET", "")
    except ImportError:
        client_id = input("GOOGLE_ADS_CLIENT_ID: ").strip()
        client_secret = input("GOOGLE_ADS_CLIENT_SECRET: ").strip()

    if not client_id or not client_secret:
        client_id = input("GOOGLE_ADS_CLIENT_ID: ").strip()
        client_secret = input("GOOGLE_ADS_CLIENT_SECRET: ").strip()

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(
        client_config,
        scopes=["https://www.googleapis.com/auth/adwords"],
    )

    flow.run_local_server(port=8080)
    credentials = flow.credentials

    print("\n=== Refresh Token ===")
    print(credentials.refresh_token)
    print("\nCopy this to .env.development as GOOGLE_ADS_REFRESH_TOKEN")
    print("This refresh token does NOT expire (unless you revoke access)")


if __name__ == "__main__":
    main()
