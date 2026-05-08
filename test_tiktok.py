import requests

ACCESS_TOKEN = "act.6E6KuiEcOJzPvTKgmlPHBgnpgwPiKKBXIWLcLEFkdXlXJSWKZuO2jwtJtRhS!6936.s1"

url = "https://open.tiktokapis.com/v2/user/info/"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

params = {
    "fields": "open_id,union_id,avatar_url,display_name,username"
}

response = requests.get(url, headers=headers, params=params)

print("STATUS:", response.status_code)
print("RESPONSE:", response.json())