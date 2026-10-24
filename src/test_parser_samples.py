"""
Test parsing logic on all downloaded sample PDFs across 2019-2024.
Verify table detection, state name mapping, column indexing, and numeric extraction.
"""

import json
import pathlib
import re

import pdfplumber

ROOT = pathlib.Path(__file__).parent.parent.resolve()
SAMPLE_DIR = ROOT / "data" / "raw" / "samples"

TARGET_STATES = [
    "Punjab",
    "Haryana",
    "Rajasthan",
    "Delhi",
    "UP",
    "Uttar Pradesh",
    "Maharashtra",
    "Gujarat",
    "MP",
    "Madhya Pradesh",
    "Tamil Nadu",
    "Karnataka",
    "Telangana",
    "Andhra Pradesh",
    "Kerala",
    "West Bengal",
    "Bihar",
    "Odisha",
]


def clean_val(v):
    if v is None:
        return None
    s = str(v).replace(",", "").strip()
    # match float or int
    m = re.search(r"[-+]?\d*\.?\d+", s)
    if m:
        try:
            return float(m.group(0))
        except ValueError:
            return None
    return None


results = {}

for pdf_file in sorted(SAMPLE_DIR.glob("*.pdf")):
    if pdf_file.stat().st_size < 1000:
        continue
    file_res = {"file": pdf_file.name, "extracted_states": {}}
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for p_idx, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                for table in tables:
                    if len(table) < 5:
                        continue
                    # Check if this table has states
                    text_blob = " ".join([str(c) for r in table for c in r if c])
                    if any(st in text_blob for st in ["Punjab", "Maharashtra", "Gujarat", "Tamil Nadu"]):
                        # Find headers
                        header = table[0]
                        # Determine column indices
                        # Typically: Col 0: Region, Col 1: State, Col 2: Max Demand Met (MW), Col 3: Shortage (MW), Col 4: Energy Met (MU)
                        # Or Col 0: State
                        for row in table[1:]:
                            if len(row) < 3:
                                continue
                            # Candidate state is row[1] or row[0]
                            c0 = str(row[0]).strip() if row[0] else ""
                            c1 = str(row[1]).strip() if len(row) > 1 and row[1] else ""
                            state_name = None
                            val_idx = 2
                            shortage_idx = 3
                            energy_idx = 4

                            for ts in TARGET_STATES:
                                if ts.lower() == c1.lower() or c1.lower().startswith(ts.lower()):
                                    state_name = ts
                                    val_idx = 2
                                    break
                                elif ts.lower() == c0.lower() or c0.lower().startswith(ts.lower()):
                                    state_name = ts
                                    val_idx = 1
                                    shortage_idx = 2
                                    energy_idx = 3
                                    break

                            if state_name and state_name not in file_res["extracted_states"]:
                                demand_mw = clean_val(row[val_idx]) if len(row) > val_idx else None
                                shortage_mw = clean_val(row[shortage_idx]) if len(row) > shortage_idx else 0.0
                                energy_mu = clean_val(row[energy_idx]) if len(row) > energy_idx else None

                                file_res["extracted_states"][state_name] = {
                                    "demand_mw": demand_mw,
                                    "shortage_mw": shortage_mw,
                                    "energy_mu": energy_mu,
                                    "page": p_idx + 1,
                                }
        results[pdf_file.name] = {
            "states_found_count": len(file_res["extracted_states"]),
            "states": file_res["extracted_states"],
        }
        print(f"File {pdf_file.name}: parsed {len(file_res['extracted_states'])} target states.")
    except Exception as e:
        results[pdf_file.name] = {"error": str(e)}
        print(f"File {pdf_file.name}: ERROR {e}")

(ROOT / "logs" / "test_parser_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
