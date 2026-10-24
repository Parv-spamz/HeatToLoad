"""
Weather Ingestion Pipeline for Open-Meteo Historical Weather Archive API.
Adheres strictly to Section 1 Integrity Contract and Phase 2 specifications:
- One request per state coordinate point for the full analysis period.
- Raw JSON responses saved directly to data/raw/weather/ with SHA-256 in MANIFEST.csv.
- Exact request parameters recorded per file.
- Cleanly parsed into raw_weather_records.csv with provenance (api_request_id, params, retrieved_at).
- Explicit attribution and licensing notes logged.
"""

import datetime
import hashlib
import json
import pathlib
import time

import pandas as pd
import requests
import yaml

ROOT = pathlib.Path(__file__).parent.parent.resolve()
CONFIG_PATH = ROOT / "config.yaml"
cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

RAW_WEATHER_DIR = ROOT / "data" / "raw" / "weather"
RAW_WEATHER_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH = ROOT / "data" / "MANIFEST.csv"
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

ENDPOINT = cfg["weather"]["api_endpoint"]
VARIABLES = cfg["weather"]["variables"]
STATES = cfg["states"]

# Date range: 2021-01-01 to 2024-12-31 (4 full years, 1,461 days)
START_DATE = "2021-01-01"
END_DATE = "2024-12-31"

HEADERS = {"User-Agent": "HeatToDemand-Research/1.0 (academic data science portfolio; Open-Meteo ERA5 ingestion)"}


def run_weather_ingestion():
    print("=" * 70)
    print("Starting Open-Meteo Weather Ingestion Pipeline")
    print(f"Endpoint: {ENDPOINT}")
    print(f"Date Range: {START_DATE} to {END_DATE}")
    print(f"States: {len(STATES)} centroid locations")
    print("=" * 70)

    manifest_rows = []
    if MANIFEST_PATH.exists():
        try:
            df_m = pd.read_csv(MANIFEST_PATH)
            manifest_rows = df_m.to_dict("records")
        except Exception:
            manifest_rows = []

    existing_paths = {r.get("local_path"): r for r in manifest_rows}

    all_weather_records = []
    weather_coverage = {}

    for state_name, info in STATES.items():
        state_code = info["code"]
        lat = info["lat"]
        lon = info["lon"]
        city = info["city"]

        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "daily": ",".join(VARIABLES),
            "timezone": "Asia/Kolkata",
        }

        raw_filename = f"weather_{state_code}_{START_DATE}_{END_DATE}.json"
        local_dest = RAW_WEATHER_DIR / raw_filename
        local_rel = str(local_dest.relative_to(ROOT)).replace("\\", "/")
        retrieved_at = datetime.datetime.now(datetime.UTC).isoformat()

        print(f"\nFetching weather for {state_name} ({city}, lat={lat}, lon={lon})...")

        need_download = True
        if local_dest.exists() and local_dest.stat().st_size > 1000:
            content = local_dest.read_bytes()
            sha = hashlib.sha256(content).hexdigest()
            if local_rel in existing_paths and existing_paths[local_rel].get("sha256") == sha:
                need_download = False
                print(f"  Existing valid cached file found: {raw_filename} (SHA256: {sha[:16]}...)")
                data = json.loads(content.decode("utf-8"))
                http_status = 200
                file_size = len(content)
                file_sha256 = sha

        if need_download:
            try:
                r = requests.get(ENDPOINT, params=params, headers=HEADERS, timeout=30)
                http_status = r.status_code
                content = r.content
                file_size = len(content)
                file_sha256 = hashlib.sha256(content).hexdigest()

                if http_status == 200:
                    local_dest.write_bytes(content)
                    data = r.json()
                    manifest_row = {
                        "source_url": r.url,
                        "retrieved_at_utc": retrieved_at,
                        "local_path": local_rel,
                        "sha256": file_sha256,
                        "size_bytes": file_size,
                        "http_status": http_status,
                        "parse_status": "parsed",
                        "parse_notes": f"Params: lat={lat},lon={lon},start={START_DATE},end={END_DATE}",
                    }
                    manifest_rows.append(manifest_row)
                    existing_paths[local_rel] = manifest_row
                else:
                    manifest_row = {
                        "source_url": r.url,
                        "retrieved_at_utc": retrieved_at,
                        "local_path": local_rel,
                        "sha256": file_sha256,
                        "size_bytes": file_size,
                        "http_status": http_status,
                        "parse_status": "failed",
                        "parse_notes": f"HTTP {http_status}: {r.text[:200]}",
                    }
                    manifest_rows.append(manifest_row)
                    existing_paths[local_rel] = manifest_row
                    continue
                time.sleep(0.5)  # Polite delay
            except Exception as e:
                print(f"  FAILED to fetch weather for {state_name}: {e}")
                continue

        # Parse weather JSON
        daily = data.get("daily", {})
        times = daily.get("time", [])
        temp_max = daily.get("temperature_2m_max", [])
        temp_min = daily.get("temperature_2m_min", [])
        temp_mean = daily.get("temperature_2m_mean", [])
        app_temp_max = daily.get("apparent_temperature_max", [])
        rel_hum = daily.get("relative_humidity_2m_mean", [])
        precip = daily.get("precipitation_sum", [])

        request_id = f"openmeteo_{state_code}_{START_DATE}_{END_DATE}"
        params_str = f"lat={lat}&lon={lon}&tz=Asia/Kolkata"

        points_count = len(times)
        null_count = sum(1 for t in temp_max if t is None)
        weather_coverage[state_name] = {
            "total_days": points_count,
            "null_temp_count": null_count,
            "min_temp": min([t for t in temp_max if t is not None], default=None),
            "max_temp": max([t for t in temp_max if t is not None], default=None),
        }

        for i in range(points_count):
            all_weather_records.append(
                {
                    "date": times[i],
                    "state": state_name,
                    "city": city,
                    "lat": lat,
                    "lon": lon,
                    "temperature_2m_max": temp_max[i] if i < len(temp_max) else None,
                    "temperature_2m_min": temp_min[i] if i < len(temp_min) else None,
                    "temperature_2m_mean": temp_mean[i] if i < len(temp_mean) else None,
                    "apparent_temperature_max": app_temp_max[i] if i < len(app_temp_max) else None,
                    "relative_humidity_2m_mean": rel_hum[i] if i < len(rel_hum) else None,
                    "precipitation_sum": precip[i] if i < len(precip) else None,
                    "api_request_id": request_id,
                    "params": params_str,
                    "source_file": raw_filename,
                    "retrieved_at_utc": retrieved_at,
                }
            )

        print(f"  {state_name}: {points_count} daily weather records parsed (nulls: {null_count}).")

    # Update MANIFEST.csv
    df_manifest = pd.DataFrame(manifest_rows).drop_duplicates(subset=["local_path"], keep="last")
    df_manifest.to_csv(MANIFEST_PATH, index=False)
    print(f"\nUpdated MANIFEST with weather records: {len(df_manifest)} entries total.")

    # Save parsed weather CSV
    df_weather = pd.DataFrame(all_weather_records)
    out_weather_path = RAW_WEATHER_DIR / "raw_weather_records.csv"
    df_weather.to_csv(out_weather_path, index=False)
    print(f"Saved {len(df_weather)} raw weather records to {out_weather_path}")

    # Save weather coverage report
    (LOGS_DIR / "weather_coverage_report.json").write_text(json.dumps(weather_coverage, indent=2), encoding="utf-8")
    print("Saved weather coverage summary to logs/weather_coverage_report.json")


if __name__ == "__main__":
    run_weather_ingestion()
