"""
Cross-platform Make Runner for Heat-to-Load Project.
Supports Windows / Linux / macOS execution of Makefile targets.
"""

import sys
import os
import subprocess
import pathlib

ROOT = pathlib.Path(__file__).parent.resolve()
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
if not VENV_PY.exists():
    VENV_PY = ROOT / ".venv" / "bin" / "python"
if not VENV_PY.exists():
    VENV_PY = pathlib.Path(sys.executable)

def run_cmd(cmd_list, description):
    print(f"\n>>> [{description}] Running: {' '.join(str(c) for c in cmd_list)}")
    res = subprocess.run(cmd_list, cwd=str(ROOT))
    if res.returncode != 0:
        print(f"\n[FAIL] Command failed with exit code {res.returncode}: {' '.join(str(c) for c in cmd_list)}")
        sys.exit(res.returncode)
    print(f"[OK] {description} succeeded.\n")

def target_setup():
    run_cmd([str(VENV_PY), "-m", "pip", "install", "-r", "requirements.txt"], "Setup dependencies")
    # Record freeze
    out = subprocess.check_output([str(VENV_PY), "-m", "pip", "freeze"], text=True)
    (ROOT / "logs" / "pip_freeze.txt").write_text(out, encoding="utf-8")
    print("Dependencies verified and logs/pip_freeze.txt updated.")

def target_ingest():
    run_cmd([str(VENV_PY), "src/ingest_demand.py"], "Ingest Demand Data")
    run_cmd([str(VENV_PY), "src/ingest_weather.py"], "Ingest Weather Data")

def target_clean():
    run_cmd([str(VENV_PY), "src/clean.py"], "Clean & Validate Data Quality")

def target_load():
    run_cmd([str(VENV_PY), "src/load_db.py"], "Load SQLite Database")

def target_features():
    run_cmd([str(VENV_PY), "src/features.py"], "Build Features Layer")

def target_model():
    run_cmd([str(VENV_PY), "src/model_baseline.py"], "Run OLS / Piecewise Baseline Models")
    run_cmd([str(VENV_PY), "src/model_gbm.py"], "Train LightGBM Point Models")
    run_cmd([str(VENV_PY), "src/model_quantile.py"], "Train Quantile Models & Evaluate SHAP")

def target_scenarios():
    run_cmd([str(VENV_PY), "src/scenarios.py"], "Simulate +1C and +2C Warming Scenarios")

def target_export():
    run_cmd([str(VENV_PY), "src/export_tableau.py"], "Export Tableau-ready CSVs")

def target_report():
    run_cmd([str(VENV_PY), "src/generate_figures.py"], "Generate High-Resolution Figures")
    run_cmd([str(VENV_PY), "src/render_reports.py"], "Render Reports and README from results.json")

def target_test():
    run_cmd([str(VENV_PY), "-m", "pytest", "tests/", "-v"], "Execute Pytest Suite")
    run_cmd([str(VENV_PY), "-m", "ruff", "check", "src/", "tests/"], "Lint with Ruff")
    run_cmd([str(VENV_PY), "-m", "black", "--check", "src/", "tests/"], "Check formatting with Black")

def target_verify():
    run_cmd([str(VENV_PY), "src/verify_integrity.py"], "Verify Project Integrity & Provenance")

def target_all():
    target_ingest()
    target_clean()
    target_load()
    target_features()
    target_model()
    target_scenarios()
    target_export()
    target_report()
    target_test()
    target_verify()

def target_serve():
    run_cmd([str(VENV_PY), "server.py"], "Launch Web Frontend Cockpit")

TARGETS = {
    "setup": target_setup,
    "ingest": target_ingest,
    "clean": target_clean,
    "load": target_load,
    "features": target_features,
    "model": target_model,
    "scenarios": target_scenarios,
    "export": target_export,
    "report": target_report,
    "test": target_test,
    "verify": target_verify,
    "serve": target_serve,
    "all": target_all,
}

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(f"Usage: python make.py [{' | '.join(TARGETS.keys())}]")
        sys.exit(1)
    for t in args:
        if t not in TARGETS:
            print(f"Unknown target: '{t}'. Available: {list(TARGETS.keys())}")
            sys.exit(1)
        TARGETS[t]()
