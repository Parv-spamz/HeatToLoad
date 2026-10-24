"""
Unit Tests for SQLite Star Schema Database.
"""

import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).parent.parent.resolve()
DB_PATH = ROOT / "data" / "processed" / "heat_to_load.db"


def test_database_tables_exist():
    assert DB_PATH.exists(), f"Database missing at {DB_PATH}"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    conn.close()

    expected_tables = ["dim_state", "dim_date", "fact_demand", "fact_weather", "fact_daily_load_weather"]
    for t in expected_tables:
        assert t in tables, f"Expected table {t} not found in database"


def test_dim_state_count():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cnt = cursor.execute("SELECT COUNT(*) FROM dim_state;").fetchone()[0]
    conn.close()
    assert cnt == 16, f"Expected 16 states in dim_state, found {cnt}"


def test_analytical_table_not_empty():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cnt = cursor.execute("SELECT COUNT(*) FROM fact_daily_load_weather;").fetchone()[0]
    conn.close()
    assert cnt > 10000, f"Analytical table has unexpectedly low row count: {cnt}"
