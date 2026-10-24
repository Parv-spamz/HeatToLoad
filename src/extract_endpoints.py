"""
Extract all webapi.grid-india.in endpoints and parameter names from JS bundle.
"""

import re

import requests

url = "https://grid-india.in/assets/index-CO5t6Yxl.js"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers, timeout=30)
text = r.text

# Find all occurrences of webapi.grid-india.in and surrounding code
matches = re.findall(r"webapi\.grid-india\.in[^\s\"\'\`\<\>]+", text)
print("webapi matches:", len(matches))
for m in set(matches):
    print("Match:", m)

# Search for report API endpoints or methods
endpoints = set(re.findall(r'["\']([a-zA-Z0-9_\-]+(?:Report|Psp|Daily|Download|File|get)[a-zA-Z0-9_\-]*)["\']', text))
print("\nPossible endpoints:", len(endpoints))
for ep in sorted(endpoints):
    if any(k in ep.lower() for k in ["psp", "daily", "report", "file", "download"]):
        print("Endpoint candidate:", ep)

# Find object defining API paths (often in an object like H = { ... })
api_defs = re.findall(r'([a-zA-Z0-9_]+)\s*:\s*["\']([a-zA-Z0-9_\-/]+Report[a-zA-Z0-9_\-/]*)["\']', text)
print("\nAPI definitions with Report:", len(api_defs))
for k, v in api_defs:
    print(f"Key: {k} -> {v}")
