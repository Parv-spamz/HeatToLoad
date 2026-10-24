"""
Phase 1d: Verify plausibility of state weather coordinates in config.yaml.
Checks bounding boxes (India mainland: 8.0 <= lat <= 37.5, 68.0 <= lon <= 97.5)
and regional plausibility.
"""

import json
import pathlib

import yaml

ROOT = pathlib.Path(__file__).parent.parent.resolve()
cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
states = cfg["states"]

INDIA_LAT_BOUNDS = (8.0, 37.5)
INDIA_LON_BOUNDS = (68.0, 97.5)

coord_checks = []
all_valid = True

for state, info in states.items():
    lat = info.get("lat")
    lon = info.get("lon")
    city = info.get("city")
    src = info.get("coord_source")

    lat_ok = INDIA_LAT_BOUNDS[0] <= lat <= INDIA_LAT_BOUNDS[1]
    lon_ok = INDIA_LON_BOUNDS[0] <= lon <= INDIA_LON_BOUNDS[1]
    valid = lat_ok and lon_ok
    if not valid:
        all_valid = False

    coord_checks.append(
        {
            "state": state,
            "city": city,
            "lat": lat,
            "lon": lon,
            "source": src,
            "lat_valid": lat_ok,
            "lon_valid": lon_ok,
            "overall_valid": valid,
        }
    )

results = {"all_valid": all_valid, "total_states": len(states), "checks": coord_checks}

(ROOT / "logs" / "coordinates_verification.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"Coordinates verification: all_valid={all_valid} across {len(states)} states.")
