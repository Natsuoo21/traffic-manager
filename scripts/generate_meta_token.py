"""
Exchange a short-lived Meta user token for a long-lived token (60 days).

Usage:
    1. Go to https://developers.facebook.com/tools/explorer/
    2. Select your app, request 'ads_management' permission
    3. Generate a User Access Token
    4. Run: python scripts/generate_meta_token.py <SHORT_LIVED_TOKEN>
    5. Copy the long-lived token to .env.development META_ACCESS_TOKEN
"""

import sys

import httpx


def exchange_token(app_id: str, app_secret: str, short_token: str) -> str:
    resp = httpx.get(
        "https://graph.facebook.com/v21.0/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_token,
        },
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"]


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_meta_token.py <SHORT_LIVED_TOKEN>")
        print("       Optionally set META_APP_ID and META_APP_SECRET in .env.development")
        sys.exit(1)

    short_token = sys.argv[1]

    # Try loading from .env
    try:
        from dotenv import dotenv_values
        env = dotenv_values("backend/.env.development")
        app_id = env.get("META_APP_ID", "")
        app_secret = env.get("META_APP_SECRET", "")
    except ImportError:
        app_id = input("META_APP_ID: ").strip()
        app_secret = input("META_APP_SECRET: ").strip()

    if not app_id or not app_secret:
        app_id = input("META_APP_ID: ").strip()
        app_secret = input("META_APP_SECRET: ").strip()

    long_token = exchange_token(app_id, app_secret, short_token)

    print("\n=== Long-lived Access Token ===")
    print(long_token)
    print("\nCopy this to .env.development as META_ACCESS_TOKEN")
    print("Valid for 60 days (or never if you have Standard API access)")


if __name__ == "__main__":
    main()
