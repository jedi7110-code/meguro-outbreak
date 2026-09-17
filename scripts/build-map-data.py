#!/usr/bin/env python3
"""Build static Meguro ward boundary and road-sector data from Overpass."""

import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SECTOR_DIR = DATA_DIR / "sectors"
RELATION_ID = 1758936
SECTOR_LAT = 0.02
SECTOR_LON = 0.02
ENDPOINTS = (
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)


def query_overpass(query):
    body = urllib.parse.urlencode({"data": query}).encode()
    last_error = None
    for endpoint in ENDPOINTS:
        for attempt in range(2):
            try:
                request = urllib.request.Request(
                    endpoint,
                    data=body,
                    headers={"User-Agent": "meguro-outbreak-map-builder/1.0"},
                )
                with urllib.request.urlopen(request, timeout=70) as response:
                    return json.load(response)
            except Exception as error:
                last_error = error
                time.sleep(2 + attempt * 2)
    raise RuntimeError(f"Overpass query failed: {last_error}")


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def main():
    DATA_DIR.mkdir(exist_ok=True)
    SECTOR_DIR.mkdir(parents=True, exist_ok=True)

    boundary_query = (
        f"[out:json][timeout:45];rel({RELATION_ID});out geom;"
    )
    boundary_data = query_overpass(boundary_query)
    relation = boundary_data["elements"][0]
    bounds = relation["bounds"]
    segments = []
    for member in relation.get("members", []):
        if member.get("role") != "outer" or not member.get("geometry"):
            continue
        segments.append([[point["lat"], point["lon"]] for point in member["geometry"]])
    write_json(DATA_DIR / "meguro-boundary.json", {"bounds": bounds, "segments": segments})

    rows = math.ceil((bounds["maxlat"] - bounds["minlat"]) / SECTOR_LAT)
    cols = math.ceil((bounds["maxlon"] - bounds["minlon"]) / SECTOR_LON)
    sectors = []
    for row in range(rows):
        south = bounds["minlat"] + row * SECTOR_LAT
        north = min(bounds["maxlat"], south + SECTOR_LAT)
        for col in range(cols):
            west = bounds["minlon"] + col * SECTOR_LON
            east = min(bounds["maxlon"], west + SECTOR_LON)
            sector_id = f"{row}-{col}"
            road_query = (
                "[out:json][timeout:55];"
                f'way["highway"]({south},{west},{north},{east});'
                "(._;>;);out body;"
            )
            filename = f"{sector_id}.json"
            sector_path = SECTOR_DIR / filename
            if sector_path.exists() and sector_path.stat().st_size > 1000:
                print(f"Reusing sector {sector_id} ({row * cols + col + 1}/{rows * cols})", flush=True)
            else:
                print(f"Fetching sector {sector_id} ({row * cols + col + 1}/{rows * cols})", flush=True)
                road_data = query_overpass(road_query)
                write_json(sector_path, road_data)
            sectors.append(
                {
                    "id": sector_id,
                    "row": row,
                    "col": col,
                    "bounds": [south, west, north, east],
                    "file": f"data/sectors/{filename}",
                }
            )
            time.sleep(1)

    write_json(
        DATA_DIR / "sector-manifest.json",
        {
            "bounds": bounds,
            "sectorLat": SECTOR_LAT,
            "sectorLon": SECTOR_LON,
            "rows": rows,
            "cols": cols,
            "sectors": sectors,
        },
    )
    print(f"Wrote {len(sectors)} sectors", flush=True)


if __name__ == "__main__":
    main()
