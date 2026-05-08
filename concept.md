Perfect. Now we generate the TikTok authorization URL properly.

This is the step where most integrations fail because of URL formatting mistakes.

🚀 STEP 4 — Create OAuth test script

Create a file:

test_tiktok_oauth.py
Paste this FULL code
import os
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")

REDIRECT_URI = "http://localhost:8501/tiktok_callback"

SCOPES = [
    "user.info.basic",
    "video.list"
]

scope_string = ",".join(SCOPES)

auth_url = (
    "https://www.tiktok.com/v2/auth/authorize/"
    f"?client_key={CLIENT_KEY}"
    "&response_type=code"
    f"&scope={urllib.parse.quote(scope_string)}"
    f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
    "&state=viralynx123"
)

print("\nTikTok OAuth URL:\n")
print(auth_url)
🚀 STEP 5 — Run it

From terminal:

python test_tiktok_oauth.py
🎯 Expected result

You should see a LONG URL like:

https://www.tiktok.com/v2/auth/authorize/?client_key=...
🚀 STEP 6 — Open the URL in browser

Copy the FULL URL into browser.

🎯 Expected behavior

TikTok should:

✔ Open login page
✔ Ask authorization
✔ Redirect to:
http://localhost:8501/tiktok_callback?code=XXXXX
⚠️ IMPORTANT

You will probably see:

This site can’t be reached

THAT IS OK.

What matters is:

The URL contains ?code=XXXXX
🧠 Example
http://localhost:8501/tiktok_callback?code=abc123xyz
🚨 VERY IMPORTANT

Copy ONLY:

abc123xyz

(the code value)

🛑 STOP THERE

Do NOT do token exchange yet.