"""
Inspect the H object definition in the JS bundle.
"""

import re

import requests

url = "https://grid-india.in/assets/index-CO5t6Yxl.js"
headers = {"User-Agent": "Mozilla/5.0"}
text = requests.get(url, headers=headers, timeout=30).text

# Find where getAllFiles is defined
matches = [m.start() for m in re.finditer(r"getAllFiles", text)]
print("getAllFiles matches count:", len(matches))

for i, pos in enumerate(matches):
    chunk = text[max(0, pos - 300) : min(len(text), pos + 300)]
    print(f"\n--- Match {i} around index {pos} ---")
    # Clean non-ascii for safe printing
    clean_chunk = chunk.encode("ascii", errors="replace").decode("ascii")
    print(clean_chunk)
