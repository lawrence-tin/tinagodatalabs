import os
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")

CODE = "DrbDooE3sMDsEiApegkxv5kDI7gYUfcUkaqLUJNhn1U9uVb3_9Kbv9z_FSrXDgKpg_Tz7aIuxd9vG0vIKKSK_-lWfSBTJshttxSsJmsLNSiPu1dy0JmS1WYeHmjHMjAbzjZLhKC7NB8kHEXM61oQFoFH8YkTFGDmb0y0bQSFgTFRw8bneG9R-Gtsjc6NaSVkvH-XEMC4iGMCS_6g0zVJMrYpBCCG00QDeBn3b653FmaNZrM8qsOey617M_X5fCH3T0xS_3HfXVvPsUvU/v!6896.s1"

CODE_VERIFIER = "w4FURqDK-rOcrxBbz2bWnEBZKkn7Ja9WC79ZDZZ-ShgqinsiTOrq-xvJFHP4tf-DAXiGWe_xXX8-Y9S-DvsqWw"

REDIRECT_URI = "https://neural-ivelisse-acetabuliform.ngrok-free.dev/tiktok_callback"

url = "https://open.tiktokapis.com/v2/oauth/token/"

payload = {
    "client_key": CLIENT_KEY,
    "client_secret": CLIENT_SECRET,
    "code": CODE,
    "grant_type": "authorization_code",
    "redirect_uri": REDIRECT_URI,
    "code_verifier": CODE_VERIFIER,
}

response = requests.post(
    url,
    headers={
        "Content-Type": "application/x-www-form-urlencoded"
    },
    data=payload
)

print("STATUS:", response.status_code)
print("RESPONSE:", response.text)