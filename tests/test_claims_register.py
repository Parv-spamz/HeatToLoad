"""
Unit Tests for Claims Register Integrity and Verification.
"""

import json
import pathlib

ROOT = pathlib.Path(__file__).parent.parent.resolve()
CLAIMS_PATH = ROOT / "CLAIMS_REGISTER.md"
RESULTS_PATH = ROOT / "reports" / "results.json"


def test_claims_register_exists_and_verified():
    assert CLAIMS_PATH.exists(), "CLAIMS_REGISTER.md is missing"
    assert RESULTS_PATH.exists(), "reports/results.json is missing"

    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    claims_text = CLAIMS_PATH.read_text(encoding="utf-8")

    # Verify each claim ID is present
    for cid in ["CLM-001", "CLM-002", "CLM-003", "CLM-004", "CLM-005", "CLM-006", "CLM-007"]:
        assert cid in claims_text, f"Claim {cid} not found in CLAIMS_REGISTER.md"

    # Verify keys exist in results
    assert "baseline_models" in results
    assert "overall_summary" in results["baseline_models"]
    assert "gbm_point_model" in results
    assert "warming_scenarios" in results
