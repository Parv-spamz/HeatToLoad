"""
Test download throughput with ThreadPoolExecutor.
"""

import concurrent.futures
import time

import requests

headers = {"User-Agent": "Mozilla/5.0"}
r = (
    requests.post(
        "https://webapi.grid-india.in/api/v1/file",
        json={"_source": "grdw", "_type": "DAILY_PSP_REPORT", "_fileDate": "2023-24", "_month": "05"},
        headers={"Content-Type": "application/json"},
    )
    .json()
    .get("retData", [])
)

pdfs = [x["FilePath"] for x in r if x.get("FilePath", "").endswith(".pdf")][:20]


def dl(path):
    url = f"https://webcdn.grid-india.in/{path}"
    res = requests.get(url, headers=headers, timeout=20)
    return len(res.content)


t0 = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    sizes = list(ex.map(dl, pdfs))

duration = time.time() - t0
print(
    f"Downloaded {len(sizes)} files totaling {sum(sizes)//1024} KB in {duration:.2f} seconds ({len(sizes)/duration:.1f} files/sec)."
)
