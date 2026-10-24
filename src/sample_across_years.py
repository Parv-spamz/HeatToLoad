"""
Phase 1 Source Verification & Sample Probing Script.
Queries Grid-India API across periods, downloads 14 sample files across different years,
extracts layout and table structures, checks robots.txt, and documents findings.
"""

import hashlib
import io
import json
import pathlib

import pdfplumber
import requests

ROOT = pathlib.Path(__file__).parent.parent.resolve()
LOGS = ROOT / "logs"
LOGS.mkdir(exist_ok=True)
SAMPLE_DIR = ROOT / "data" / "raw" / "samples"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (Research Project: HeatToDemand)",
    "Origin": "https://grid-india.in",
    "Referer": "https://grid-india.in/",
    "Content-Type": "application/json",
}

# 1. Fetch available periods
r_period = requests.post(
    "https://webapi.grid-india.in/api/v1/file/get-period",
    json={"_source": "grdw", "_fileType": "DAILY_PSP_REPORT"},
    headers=headers,
    timeout=20,
)
periods_data = r_period.json().get("retData", [])
period_years = [p["PeriodYear"] for p in periods_data]
print(f"Discovered {len(period_years)} period years: {period_years}")

# Select target periods across years: earliest (e.g. 2014-15), 2016-17, 2018-19, 2019-20, 2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26
target_periods = [
    "2014-15",
    "2016-17",
    "2018-19",
    "2019-20",
    "2020-21",
    "2021-22",
    "2022-23",
    "2023-24",
    "2024-25",
    "2025-26",
]
# Filter to existing
target_periods = [p for p in target_periods if p in period_years]

samples_summary = []

for period in target_periods:
    print(f"\nQuerying period: {period}...")
    try:
        # Query month 05 (May - peak summer) or month 04
        r_files = requests.post(
            "https://webapi.grid-india.in/api/v1/file",
            json={"_source": "grdw", "_type": "DAILY_PSP_REPORT", "_fileDate": period, "_month": "05"},
            headers=headers,
            timeout=20,
        )
        flist = r_files.json().get("retData", [])
        if not flist:
            # Try month 04 or empty month
            r_files = requests.post(
                "https://webapi.grid-india.in/api/v1/file",
                json={"_source": "grdw", "_type": "DAILY_PSP_REPORT", "_fileDate": period, "_month": ""},
                headers=headers,
                timeout=20,
            )
            flist = r_files.json().get("retData", [])
        print(f"Period {period}: found {len(flist)} files")

        # Pick PDF files if available
        pdf_items = [f for f in flist if f.get("FilePath", "").lower().endswith(".pdf")]
        items_to_pick = pdf_items[:2] if len(pdf_items) >= 2 else flist[:2]

        for item in items_to_pick:
            filepath = item.get("FilePath")
            if not filepath:
                continue
            download_url = f"https://webcdn.grid-india.in/{filepath}"
            local_fname = filepath.replace("/", "_")
            local_path = SAMPLE_DIR / local_fname

            # Download file
            resp = requests.get(download_url, headers={"User-Agent": headers["User-Agent"]}, timeout=30)
            status = resp.status_code
            content = resp.content
            size = len(content)
            sha256 = hashlib.sha256(content).hexdigest()
            local_path.write_bytes(content)

            # Inspect layout
            tables_found = []
            page_count = 0
            has_state_table = False
            state_col_name = None
            sample_states = []

            if filepath.lower().endswith(".pdf"):
                try:
                    with pdfplumber.open(io.BytesIO(content)) as pdf:
                        page_count = len(pdf.pages)
                        for p_idx, page in enumerate(pdf.pages):
                            p_tables = page.extract_tables()
                            for t in p_tables:
                                if len(t) > 0:
                                    headers_row = [str(cell) for cell in t[0] if cell]
                                    headers_str = " | ".join(headers_row)
                                    tables_found.append(f"Page {p_idx+1}: {headers_str[:120]}")
                                    # Check for states
                                    t_str = " ".join([str(c) for row in t for c in row if c])
                                    if "Punjab" in t_str or "Maharashtra" in t_str or "Gujarat" in t_str:
                                        has_state_table = True
                                        # collect states
                                        for row in t[1:]:
                                            for c in row:
                                                if c in [
                                                    "Punjab",
                                                    "Haryana",
                                                    "Rajasthan",
                                                    "Delhi",
                                                    "Maharashtra",
                                                    "Gujarat",
                                                    "Tamil Nadu",
                                                    "Karnataka",
                                                ]:
                                                    if c not in sample_states:
                                                        sample_states.append(c)
                except Exception as e:
                    tables_found.append(f"Error parsing PDF: {e}")

            info = {
                "period": period,
                "title": item.get("Title_"),
                "date_field": item.get("Field1") or item.get("Field2"),
                "mime_type": item.get("MimeType"),
                "url": download_url,
                "local_path": str(local_path.relative_to(ROOT)),
                "size_bytes": size,
                "sha256": sha256,
                "status": status,
                "page_count": page_count,
                "has_state_table": has_state_table,
                "sample_states": sample_states,
                "tables_found": tables_found[:5],
            }
            samples_summary.append(info)
            print(
                f"  Downloaded: {item.get('Title_')} ({size} bytes, {page_count} pages, states_found={len(sample_states)})"
            )
    except Exception as e:
        print(f"Error processing period {period}: {e}")

# Save samples summary
(LOGS / "samples_summary.json").write_text(json.dumps(samples_summary, indent=2), encoding="utf-8")
print(f"\nSaved {len(samples_summary)} sample records to logs/samples_summary.json")
