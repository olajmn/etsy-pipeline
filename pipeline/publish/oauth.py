"""
etsy/oauth.py — One-time OAuth 2.0 setup for Etsy API access.

Run from project root: python3 etsy/oauth.py
Saves ETSY_ACCESS_TOKEN and ETSY_REFRESH_TOKEN to .env
"""
import base64
import hashlib
import json
import os
import secrets
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from dotenv import load_dotenv, set_key

load_dotenv()

ETSY_CLIENT_ID = os.environ.get("ETSY_CLIENT_ID", "")
REDIRECT_URI   = "http://localhost:3003/oauth/redirect"
SCOPES         = "listings_w listings_r shops_r transactions_r"
ENV_FILE       = Path(".env")

if not ETSY_CLIENT_ID:
    print("ERROR: ETSY_CLIENT_ID not found in .env")
    sys.exit(1)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _pkce():
    verifier  = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def _build_auth_url(challenge: str, state: str) -> str:
    params = {
        "response_type":         "code",
        "client_id":             ETSY_CLIENT_ID,
        "redirect_uri":          REDIRECT_URI,
        "scope":                 SCOPES,
        "state":                 state,
        "code_challenge":        challenge,
        "code_challenge_method": "S256",
    }
    return "https://www.etsy.com/oauth/connect?" + urllib.parse.urlencode(params)


def _exchange_code(code: str, verifier: str) -> dict:
    data = urllib.parse.urlencode({
        "grant_type":    "authorization_code",
        "client_id":     ETSY_CLIENT_ID,
        "redirect_uri":  REDIRECT_URI,
        "code":          code,
        "code_verifier": verifier,
    }).encode()
    req = urllib.request.Request(
        "https://api.etsy.com/v3/public/oauth/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main():
    verifier, challenge = _pkce()
    state    = secrets.token_hex(8)
    auth_url = _build_auth_url(challenge, state)

    code_holder = {}
    server_done = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/oauth/redirect":
                params = urllib.parse.parse_qs(parsed.query)
                code_holder["code"]  = params.get("code",  [None])[0]
                code_holder["state"] = params.get("state", [None])[0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<h2>Authorized! You can close this tab.</h2>")
                server_done.set()

        def log_message(self, *args):
            pass

    server = HTTPServer(("localhost", 3003), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    print("\nOpening Etsy in your browser...")
    print(f"If it doesn't open automatically, go to:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server_done.wait(timeout=120)
    server.shutdown()

    if not code_holder.get("code"):
        print("ERROR: No code received. Did you approve the app in the browser?")
        sys.exit(1)

    if code_holder["state"] != state:
        print("ERROR: State mismatch.")
        sys.exit(1)

    print("Exchanging code for tokens...")
    tokens = _exchange_code(code_holder["code"], verifier)

    access_token  = tokens["access_token"]
    refresh_token = tokens.get("refresh_token", "")

    set_key(str(ENV_FILE), "ETSY_ACCESS_TOKEN",  access_token)
    set_key(str(ENV_FILE), "ETSY_REFRESH_TOKEN", refresh_token)

    print("\nDone! Tokens saved to .env")
    print(f"  Access token:  {access_token[:12]}...")
    if refresh_token:
        print(f"  Refresh token: {refresh_token[:12]}...")


if __name__ == "__main__":
    main()
