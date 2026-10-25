"""Download monthly agroclimatic series from NASA POWER API for Benin markets.

This module extracts the WGS84 coordinates of all active Benin markets from
``data/raw/wfp_food_prices_ben.csv``, deduplicates them onto NASA POWER's native
MERRA-2 ``0.5° × 0.625°`` latitude/longitude grid, queries the official NASA
POWER Monthly Point endpoint recorded in ``docs/DATA.md``, saves the consolidated
agroclimatic table to ``data/raw/nasa_power_benin_markets.csv``, verifies file
size, and computes SHA-256 and MD5 checksums.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

from src.config import (
    NASA_GRID_LAT_STEP,
    NASA_GRID_LON_STEP,
    NASA_POWER_COMMUNITY,
    NASA_POWER_END_YEAR,
    NASA_POWER_MONTHLY_URL,
    NASA_POWER_PARAMETERS,
    NASA_POWER_RAW_CSV,
    NASA_POWER_START_YEAR,
    WFP_PRICES_RAW_CSV,
)
from src.ingest.download_wfp import compute_checksums


MONTH_KEYS: tuple[tuple[int, str], ...] = (
    (1, "JAN"),
    (2, "FEB"),
    (3, "MAR"),
    (4, "APR"),
    (5, "MAY"),
    (6, "JUN"),
    (7, "JUL"),
    (8, "AUG"),
    (9, "SEP"),
    (10, "OCT"),
    (11, "NOV"),
    (12, "DEC"),
)


@dataclass(frozen=True)
class GridCellMarkets:
    """Represents a unique MERRA-2 0.5 x 0.625 deg grid cell and its mapped markets."""

    grid_lat: float
    grid_lon: float
    market_ids: tuple[str, ...]
    market_names: tuple[str, ...]


def snap_to_merra2_grid(lat: float, lon: float) -> tuple[float, float]:
    """Snap a WGS84 (latitude, longitude) coordinate to the nearest MERRA-2 grid center."""
    grid_lat = round(round(lat / NASA_GRID_LAT_STEP) * NASA_GRID_LAT_STEP, 4)
    grid_lon = round(round(lon / NASA_GRID_LON_STEP) * NASA_GRID_LON_STEP, 4)
    return grid_lat, grid_lon


def extract_unique_grid_cells(prices_csv: Path = WFP_PRICES_RAW_CSV) -> list[GridCellMarkets]:
    """Extract active markets from WFP prices CSV and group by MERRA-2 grid cell."""
    markets_by_id: dict[str, tuple[str, float, float]] = {}
    with prices_csv.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("date", "").startswith("#"):
                continue
            mid = row["market_id"]
            if mid not in markets_by_id:
                markets_by_id[mid] = (
                    row["market"],
                    float(row["latitude"]),
                    float(row["longitude"]),
                )

    grid_map: dict[tuple[float, float], list[tuple[str, str]]] = {}
    for mid, (mname, lat, lon) in sorted(markets_by_id.items(), key=lambda x: int(x[0])):
        g_lat, g_lon = snap_to_merra2_grid(lat, lon)
        grid_map.setdefault((g_lat, g_lon), []).append((mid, mname))

    cells: list[GridCellMarkets] = []
    for (g_lat, g_lon), m_list in sorted(grid_map.items()):
        cells.append(
            GridCellMarkets(
                grid_lat=g_lat,
                grid_lon=g_lon,
                market_ids=tuple(x[0] for x in m_list),
                market_names=tuple(x[1] for x in m_list),
            )
        )
    return cells


def build_nasa_power_url(grid_lat: float, grid_lon: float) -> str:
    """Construct the exact NASA POWER monthly agroclimatology API URL."""
    query = urllib.parse.urlencode(
        {
            "parameters": ",".join(NASA_POWER_PARAMETERS),
            "community": NASA_POWER_COMMUNITY,
            "longitude": f"{grid_lon:.4f}",
            "latitude": f"{grid_lat:.4f}",
            "start": str(NASA_POWER_START_YEAR),
            "end": str(NASA_POWER_END_YEAR),
            "format": "JSON",
        }
    )
    return f"{NASA_POWER_MONTHLY_URL}?{query}"


def fetch_grid_cell_monthly(
    grid_lat: float,
    grid_lon: float,
    timeout_seconds: int = 60,
) -> dict[str, dict[str, float]]:
    """Query NASA POWER monthly endpoint for one grid cell and return parameter dict."""
    url = build_nasa_power_url(grid_lat, grid_lon)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "BeninAgroMarket-Ingest/1.0 (Python urllib)"},
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload["properties"]["parameter"]


def download_nasa_power_markets(
    prices_csv: Path = WFP_PRICES_RAW_CSV,
    output_csv: Path = NASA_POWER_RAW_CSV,
    polite_delay_seconds: float = 0.25,
) -> tuple[int, str, str]:
    """Download NASA POWER monthly data for all active Benin market grid cells."""
    cells = extract_unique_grid_cells(prices_csv=prices_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    headers = [
        "grid_lat",
        "grid_lon",
        "year",
        "month",
        "year_month",
        *NASA_POWER_PARAMETERS,
        "mapped_market_ids",
        "mapped_markets_count",
    ]
    rows: list[list[str | int | float]] = []

    for idx, cell in enumerate(cells):
        param_data = fetch_grid_cell_monthly(cell.grid_lat, cell.grid_lon)
        market_ids_str = ";".join(cell.market_ids)
        for yr in range(NASA_POWER_START_YEAR, NASA_POWER_END_YEAR + 1):
            for m_num, m_abbr in MONTH_KEYS:
                if (yr, m_num) > (2026, 9):
                    continue
                key = f"{yr}{m_abbr}"
                # NASA POWER monthly JSON uses keys like "201901" or "2019JAN" depending on version; check both
                key_num = f"{yr}{m_num:02d}"
                vals: list[float] = []
                for p in NASA_POWER_PARAMETERS:
                    p_dict = param_data.get(p, {})
                    val = p_dict.get(key_num, p_dict.get(key, -999.0))
                    vals.append(float(val))
                rows.append(
                    [
                        f"{cell.grid_lat:.4f}",
                        f"{cell.grid_lon:.4f}",
                        yr,
                        m_num,
                        f"{yr:04d}-{m_num:02d}",
                        *(f"{v:.4f}" for v in vals),
                        market_ids_str,
                        len(cell.market_ids),
                    ]
                )
        if idx + 1 < len(cells) and polite_delay_seconds > 0:
            time.sleep(polite_delay_seconds)

    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    size_bytes = output_csv.stat().st_size
    if size_bytes < 10_000:
        raise ValueError(f"NASA POWER output file {output_csv} is unexpectedly small: {size_bytes} bytes")
    sha256_hex, md5_hex = compute_checksums(output_csv)
    return size_bytes, sha256_hex, md5_hex


if __name__ == "__main__":
    size_b, sha256_d, md5_d = download_nasa_power_markets()
    print(
        f"[OK] NASA POWER Benin Markets Monthly Agroclimatology\n"
        f"     Path:    {NASA_POWER_RAW_CSV}\n"
        f"     Size:    {size_b:,} bytes\n"
        f"     SHA-256: {sha256_d}\n"
        f"     MD5:     {md5_d}"
    )
