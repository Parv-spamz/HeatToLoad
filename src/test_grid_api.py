"""
Test webapi.grid-india.in endpoints to retrieve PSP report metadata and file links.
"""

import json

import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Origin": "https://grid-india.in",
    "Referer": "https://grid-india.in/",
    "Content-Type": "application/json",
}

# 1. Test getPageMetaData
print("--- 1. Testing getPageMetaData ---")
try:
    payload = {"_source": "grdw", "_relPath": "/reports/daily-reports/psp-report"}
    r = requests.post("https://webapi.grid-india.in/api/v1/page", json=payload, headers=headers, timeout=15)
    print("Page status:", r.status_code)
    data = r.json()
    print("Page response keys:", data.keys())
    if data.get("retData"):
        print("Page retData[0]:", json.dumps(data["retData"][0], indent=2))
except Exception as e:
    print("Error:", e)

# 2. Test menu json from webcdn
print("\n--- 2. Testing menu JSON from webcdn ---")
try:
    r_menu = requests.get("https://webcdn.grid-india.in/files/grdw/misc/menu_en.json", headers=headers, timeout=15)
    print("Menu status:", r_menu.status_code)
    if r_menu.status_code == 200:
        menu_data = r_menu.json()
        print("Menu items count:", len(menu_data))
        # Look for PSP in menu
        for item in menu_data:
            item_str = json.dumps(item)
            if "PSP" in item_str or "psp" in item_str or "Daily" in item_str:
                print("Matching menu item:", json.dumps(item, indent=2))
except Exception as e:
    print("Error:", e)
