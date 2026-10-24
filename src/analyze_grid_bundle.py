"""
Analyze the Grid-India SPA JavaScript bundle to discover API endpoints and report URLs.
"""

import re

import requests

url = "https://grid-india.in/assets/index-CO5t6Yxl.js"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers, timeout=30)
text = r.text
print(f"Bundle length: {len(text)} bytes")

# Find API baseURL or URLs
urls = set(re.findall(r'https?://[^\s"\'<>]+', text))
print(f"Total full URLs found: {len(urls)}")
for u in sorted(urls):
    if any(k in u.lower() for k in ["grid", "posoco", "api", "report", "nldc", "file", "upload"]):
        print("URL:", u)

# Search for API path patterns like /api/ or similar
api_paths = set(re.findall(r'["\'](/api/[^"\']+)["\']', text))
print(f"API paths found: {len(api_paths)}")
for p in sorted(api_paths):
    print("API Path:", p)

# Search for mentions of PSP or daily report
psp_matches = set(re.findall(r'[^"\']*(?:psp|daily[_-]?report)[^"\']*', text, re.IGNORECASE))
print(f"PSP related strings: {len(psp_matches)}")
for s in sorted(psp_matches)[:25]:
    if len(s) < 100:
        print("PSP Match:", s)
