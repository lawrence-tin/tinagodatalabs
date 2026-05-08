import os
import secrets
import hashlib
import base64
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")

REDIRECT_URI = "https://neural-ivelisse-acetabuliform.ngrok-free.dev/tiktok_callback"

# Generate code verifier
code_verifier = secrets.token_urlsafe(64)

# Generate SHA256 challenge
hashed = hashlib.sha256(code_verifier.encode("utf-8")).digest()

code_challenge = base64.urlsafe_b64encode(hashed).decode("utf-8").replace("=", "")

params = {
    "client_key": CLIENT_KEY,
    "response_type": "code",
    "scope": "user.info.basic,video.list",
    "redirect_uri": REDIRECT_URI,
    "state": "viralynx123",
    "code_challenge": code_challenge,
    "code_challenge_method": "S256"
}

auth_url = (
    "https://www.tiktok.com/v2/auth/authorize/?"
    + urllib.parse.urlencode(params)
)

print("\nCODE VERIFIER:\n")
print(code_verifier)

print("\nAUTH URL:\n")
print(auth_url)