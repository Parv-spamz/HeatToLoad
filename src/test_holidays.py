"""
Phase 1c: Verify what the holidays Python package provides for India (IN)
across subdivisions and years (2019-2024).
"""

import json
import pathlib

import holidays

ROOT = pathlib.Path(__file__).parent.parent.resolve()

in_holidays_supported_subdivisions = holidays.country_holidays("IN").subdivisions
print(f"Supported subdivisions for India: {in_holidays_supported_subdivisions}")

years = list(range(2019, 2025))
coverage = {}

for yr in years:
    h_nat = holidays.country_holidays("IN", years=yr)
    h_dict = {dt.isoformat(): name for dt, name in sorted(h_nat.items())}
    coverage[str(yr)] = {
        "count": len(h_dict),
        "sample_festivals": {
            "Diwali": any("Diwali" in name or "Deepavali" in name for name in h_dict.values()),
            "Holi": any("Holi" in name for name in h_dict.values()),
            "Eid": any("Eid" in name or "Id" in name for name in h_dict.values()),
            "Independence Day": any("Independence" in name for name in h_dict.values()),
            "Republic Day": any("Republic" in name for name in h_dict.values()),
            "Gandhi Jayanti": any("Gandhi" in name for name in h_dict.values()),
        },
        "holidays": h_dict,
    }

# Check subdivisions for a sample state, e.g. DL, MH, TN, KA
subdiv_samples = {}
for sub in ["DL", "MH", "TN", "KA", "GJ", "UP", "WB"]:
    if sub in in_holidays_supported_subdivisions:
        h_sub = holidays.country_holidays("IN", subdiv=sub, years=2023)
        subdiv_samples[sub] = {dt.isoformat(): name for dt, name in sorted(h_sub.items())}
    else:
        subdiv_samples[sub] = "NOT_SUPPORTED"

report = {
    "supported_subdivisions": in_holidays_supported_subdivisions,
    "years_tested": years,
    "annual_coverage": coverage,
    "subdivision_samples_2023": subdiv_samples,
    "findings": {
        "is_complete": False,
        "notes": "Holidays package covers Gazetted / National holidays (Republic Day, Independence Day, Gandhi Jayanti, etc.) and major festivals with lunar/solar calculations, but state-level optional holidays and local regional festivals vary by state government notifications.",
    },
}

(ROOT / "logs" / "holidays_verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("Holidays verification completed and saved to logs/holidays_verification.json")
