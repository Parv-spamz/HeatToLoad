"""
Test fetching Grid-India pages, robots.txt, and sample PSP report URLs.
"""

import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (Research Project: HeatToDemand / academic inquiry)"
}

urls_to_test = [
    "https://grid-india.in/robots.txt",
    "https://posoco.in/robots.txt",
    "https://grid-india.in/reports/daily-reports/psp-report/",
    "https://grid-india.in/reports/daily-reports/",
    "https://posoco.in/reports/daily-reports/daily-psp-report/",
    "https://nldc.in/",
]

for url in urls_to_test:
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"URL: {url} | Status: {r.status_code} | Length: {len(r.content)}")
    except Exception as e:
        print(f"URL: {url} | Error: {type(e).__name__}: {e}")
