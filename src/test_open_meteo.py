"""
Phase 1b: Verify Open-Meteo Historical Weather Archive API.
Tests one call per state coordinate defined in config.yaml, records endpoint, parameters,
variables, units, temporal resolution, rate limits, and response sizes.
"""

import json
import pathlib
import time

import requests
import yaml

ROOT = pathlib.Path(__file__).parent.parent.resolve()
cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))

endpoint = cfg["weather"]["api_endpoint"]
variables = cfg["weather"]["variables"]
states = cfg["states"]

results = []
print(f"Testing Open-Meteo endpoint: {endpoint} for {len(states)} states...")

for state_name, info in states.items():
    lat = info["lat"]
    lon = info["lon"]
    # Test for a 3-day sample in 2023 (summer peak)
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": "2023-05-28",
        "end_date": "2023-05-30",
        "daily": ",".join(variables),
        "timezone": "Asia/Kolkata",
    }

    t0 = time.time()
    try:
        r = requests.get(endpoint, params=params, timeout=15)
        elapsed = round(time.time() - t0, 3)
        status = r.status_code
        data = r.json()

        daily_units = data.get("daily_units", {})
        daily_data = data.get("daily", {})
        time_points = len(daily_data.get("time", []))

        res_entry = {
            "state": state_name,
            "city": info["city"],
            "lat": lat,
            "lon": lon,
            "status_code": status,
            "response_time_sec": elapsed,
            "time_points": time_points,
            "daily_units": daily_units,
            "sample_temp_max": daily_data.get("temperature_2m_max", []),
            "elevation": data.get("elevation"),
            "timezone": data.get("timezone"),
        }
        results.append(res_entry)
        print(
            f"  [{state_name}] Status={status}, points={time_points}, temp_max={daily_data.get('temperature_2m_max')}, elapsed={elapsed}s"
        )
    except Exception as e:
        print(f"  [{state_name}] FAILED: {e}")
        results.append({"state": state_name, "error": str(e)})

(ROOT / "logs" / "weather_verification.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print("\nWeather verification completed and saved to logs/weather_verification.json")
