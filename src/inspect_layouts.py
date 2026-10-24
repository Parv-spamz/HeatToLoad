"""
Compare layout, table headers, column names, units, and state lists across sampled years.
"""

import json
import pathlib

import pdfplumber

ROOT = pathlib.Path(__file__).parent.parent.resolve()
samples = json.loads((ROOT / "logs" / "samples_summary.json").read_text(encoding="utf-8"))

layout_report = []

for s in samples:
    p = ROOT / s["local_path"]
    if not p.exists() or not str(p).lower().endswith(".pdf") or p.stat().st_size < 1000:
        continue

    try:
        with pdfplumber.open(p) as pdf:
            entry = {
                "period": s["period"],
                "file": p.name,
                "pages": len(pdf.pages),
                "state_table_page": None,
                "headers": None,
                "states_found": [],
                "units_found": [],
            }
            for p_idx, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                for t in tables:
                    if len(t) > 1:
                        # check if state table
                        all_text = " ".join([str(c) for r in t for c in r if c])
                        if "Punjab" in all_text and "Maharashtra" in all_text:
                            entry["state_table_page"] = p_idx + 1
                            entry["headers"] = [c.replace("\n", " ") if c else "" for c in t[0]]
                            # extract state column
                            for row in t[1:]:
                                if len(row) > 1:
                                    st_candidate = (
                                        row[1] if row[0] in ["NR", "WR", "SR", "ER", "NER", None, ""] else row[0]
                                    )
                                    if st_candidate and st_candidate not in ["Total", "TOTAL", "State", "States"]:
                                        entry["states_found"].append(str(st_candidate).strip())
                            # check units
                            for cell in t[0]:
                                if cell and ("MW" in cell or "MU" in cell or "GW" in cell):
                                    entry["units_found"].append(cell.replace("\n", " "))
                            break
                if entry["state_table_page"]:
                    break
            layout_report.append(entry)
    except Exception as e:
        layout_report.append({"file": p.name, "error": str(e)})

(ROOT / "logs" / "layout_comparison.json").write_text(json.dumps(layout_report, indent=2), encoding="utf-8")
print(f"Layout comparison completed for {len(layout_report)} files. Saved to logs/layout_comparison.json")
