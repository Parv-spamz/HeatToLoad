"""
Inspect 31.05.23_NLDC_PSP.pdf with pdfplumber and extract tables & text from all pages.
"""

import io
import pathlib

import pdfplumber
import requests

url = "https://webcdn.grid-india.in/files/grdw/uploads/daily-reports/psp-reports/2023-2024/31.05.23_NLDC_PSP.pdf"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers, timeout=20)

out_lines = []
out_lines.append(f"Source URL: {url}")
out_lines.append(f"HTTP Status: {r.status_code}")
out_lines.append(f"Content-Length: {len(r.content)} bytes\n")

pdf = pdfplumber.open(io.BytesIO(r.content))
out_lines.append(f"Total Pages: {len(pdf.pages)}\n")

for i, page in enumerate(pdf.pages):
    out_lines.append(f"=== PAGE {i+1} ===")
    text = page.extract_text()
    out_lines.append("--- Extracted Text ---")
    out_lines.append(text if text else "[No text]")

    tables = page.extract_tables()
    out_lines.append(f"\n--- Extracted Tables ({len(tables)}) ---")
    for t_idx, table in enumerate(tables):
        out_lines.append(f"Table {t_idx+1} (rows: {len(table)}):")
        for row in table[:15]:
            out_lines.append(str(row))
        if len(table) > 15:
            out_lines.append(f"... {len(table)-15} more rows ...")
    out_lines.append("\n" + "=" * 50 + "\n")

pathlib.Path("logs/sample_pdf_inspection.txt").write_text("\n".join(out_lines), encoding="utf-8")
print(f"Inspection written to logs/sample_pdf_inspection.txt ({len(pdf.pages)} pages)")
