"""
Deep inspect page metadata and menu json from Grid-India.
"""

import json

import requests

headers = {
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://grid-india.in",
    "Referer": "https://grid-india.in/",
    "Content-Type": "application/json",
}

# 1. Page metadata
payload = {"_source": "grdw", "_relPath": "/reports/daily-reports/psp-report"}
r = requests.post("https://webapi.grid-india.in/api/v1/page", json=payload, headers=headers, timeout=15)
print("Page Data:", json.dumps(r.json(), indent=2))

# 2. Search menu hierarchy recursively
r_menu = requests.get("https://webcdn.grid-india.in/files/grdw/misc/menu_en.json", headers=headers, timeout=15)
menu = r_menu.json()


def search_menu(items, path=""):
    for item in items:
        title = item.get("Title", "")
        current_path = f"{path} > {title}" if path else title
        url = item.get("Url", "")
        f_type = item.get("FileType", "")
        if any(k in title.lower() or k in url.lower() for k in ["psp", "daily", "power supply"]):
            print(f"FOUND: {current_path} | URL: {url} | FileType: {f_type}")
        if item.get("children"):
            search_menu(item["children"], current_path)
        if item.get("sub_menu"):
            search_menu(item["sub_menu"], current_path)


print("\n--- Recursive menu search ---")
search_menu(menu)
