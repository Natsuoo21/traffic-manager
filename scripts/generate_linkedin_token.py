"""
Run LinkedIn 3-legged OAuth to get access + refresh tokens.

Usage:
    1. Go to linkedin.com/developers/apps → Create app
    2. Request "Marketing Developer Platform" product
    3. Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in .env.development
    4. Add http://localhost:8080/callback as redirect URL in app Auth tab
    5. Run: python scripts/generate_linkedin_token.py
    6. Authorize in the browser
    7. Copy tokens to .env.development
"""

import secrets
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs

import httpx

REDIRECT_URI = "http://localhost:8080/callback"
AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
SCOPES = "r_ads,r_ads_reporting,rw_ads,r_organization_social"

auth_code: str | None = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        global auth_code
        query = parse_qs(urlparse(self.path).query)
        auth_code = query.get("code", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>Success! You can close this tab.</h1>")

    def log_message(self, format: str, *args: object) -> None:
        pass  # Suppress logs


def main() -> None:
    # Try loading from .env
    try:
        from dotenv import dotenv_values
        env = dotenv_values("backend/.env.development")
        client_id = env.get("LINKEDIN_CLIENT_ID", "")
        client_secret = env.get("LINKEDIN_CLIENT_SECRET", "")
    except ImportError:
        client_id = input("LINKEDIN_CLIENT_ID: ").strip()
        client_secret = input("LINKEDIN_CLIENT_SECRET: ").strip()

    if not client_id or not client_secret:
        client_id = input("LINKEDIN_CLIENT_ID: ").strip()
        client_secret = input("LINKEDIN_CLIENT_SECRET: ").strip()

    state = secrets.token_urlsafe(16)
    auth_params = urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
    })

    auth_url = f"{AUTH_URL}?{auth_params}"
    print(f"Opening browser for authorization...\n{auth_url}")
    webbrowser.open(auth_url)

    # Start local server to capture callback
    server = HTTPServer(("localhost", 8080), CallbackHandler)
    print("Waiting for callback on http://localhost:8080/callback ...")
    server.handle_request()

    if not auth_code:
        print("ERROR: No authorization code received")
        sys.exit(1)

    # Exchange code for tokens
    resp = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    resp.raise_for_status()
    tokens = resp.json()

    print("\n=== Access Token (60 days) ===")
    print(tokens.get("access_token", "N/A"))

    if "refresh_token" in tokens:
        print("\n=== Refresh Token (365 days) ===")
        print(tokens["refresh_token"])
    else:
        print("\nNo refresh token (requires Marketing Developer Platform partner access)")

    print("\nCopy these to .env.development as LINKEDIN_ACCESS_TOKEN / LINKEDIN_REFRESH_TOKEN")


if __name__ == "__main__":
    main()
