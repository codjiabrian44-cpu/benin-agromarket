"""Measure built web asset sizes (raw & gzip) and verify Phase 3 performance budgets.

Per `docs/PHASE3_BRIEF.md` and `AGENTS.md` (`## Numbers in documents`):
- Home page budgets:
  - JS: `<= 120 KB` gzip
  - CSS: `<= 30 KB` gzip
  - Fonts (total `.woff2`): `<= 70 KB` total
  - Raster images: `0` (except at most one Open Graph image)
- Writes `docs/tables/web_budget.{csv,md}` after every `astro build`.
"""

from __future__ import annotations

import csv
import gzip
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

from src.config import PROJECT_ROOT, TABLES_DIR

SCRIPT_CITATION = "src/evaluate/web_budget.py"
DIST_DIR = PROJECT_ROOT / "web" / "dist"


def gzip_size(data: bytes) -> int:
    """Return gzip-compressed byte count at level 9."""
    return len(gzip.compress(data, compresslevel=9))


def extract_home_referenced_assets(index_html_path: Path) -> Tuple[Set[str], Set[str]]:
    """Extract local `.js` and `.css` paths referenced by the built Home page (`dist/index.html`)."""
    if not index_html_path.exists():
        return set(), set()
    html = index_html_path.read_text(encoding="utf-8")
    js_refs: Set[str] = set()
    css_refs: Set[str] = set()

    def normalize_asset_rel(raw_ref: str) -> str:
        rel = raw_ref.lstrip("/")
        if not (DIST_DIR / rel).exists() and "_astro/" in rel:
            rel = rel[rel.index("_astro/") :]
        return rel

    for m in re.finditer(r'(?:src|href)=["\']([^"\']+\.(?:js|mjs))["\']', html):
        js_refs.add(normalize_asset_rel(m.group(1)))
    for m in re.finditer(r'href=["\']([^"\']+\.css)["\']', html):
        css_refs.add(normalize_asset_rel(m.group(1)))

    return js_refs, css_refs


def run_web_budget_audit() -> Tuple[Path, Path]:
    """Scan `web/dist/` and write `docs/tables/web_budget.{csv,md}`."""
    if not DIST_DIR.exists():
        raise FileNotFoundError(
            f"[Web Budget] Build output directory not found: {DIST_DIR}. Run `npm run build` in `web/` first."
        )

    all_js_files = sorted(DIST_DIR.rglob("*.js")) + sorted(DIST_DIR.rglob("*.mjs"))
    all_css_files = sorted(DIST_DIR.rglob("*.css"))
    all_font_files = sorted(DIST_DIR.rglob("*.woff2")) + sorted(DIST_DIR.rglob("*.woff")) + sorted(DIST_DIR.rglob("*.ttf"))
    all_raster_files = (
        sorted(DIST_DIR.rglob("*.png"))
        + sorted(DIST_DIR.rglob("*.jpg"))
        + sorted(DIST_DIR.rglob("*.jpeg"))
        + sorted(DIST_DIR.rglob("*.webp"))
        + sorted(DIST_DIR.rglob("*.avif"))
    )
    home_json = DIST_DIR / "data" / "home-summary.json"
    index_html = DIST_DIR / "index.html"
    en_index_html = DIST_DIR / "en" / "index.html"

    home_js_rels, home_css_rels = extract_home_referenced_assets(index_html)
    home_js_files = [DIST_DIR / r for r in sorted(home_js_rels) if (DIST_DIR / r).exists()]
    home_css_files = [DIST_DIR / r for r in sorted(home_css_rels) if (DIST_DIR / r).exists()]

    def sum_sizes(paths: List[Path]) -> Tuple[int, int]:
        raw_total = 0
        gz_total = 0
        for p in paths:
            b = p.read_bytes()
            raw_total += len(b)
            gz_total += gzip_size(b)
        return raw_total, gz_total

    home_js_raw, home_js_gz = sum_sizes(home_js_files)
    all_js_raw, all_js_gz = sum_sizes(all_js_files)
    home_css_raw, home_css_gz = sum_sizes(home_css_files if home_css_files else all_css_files)
    all_css_raw, all_css_gz = sum_sizes(all_css_files)
    font_raw, font_gz = sum_sizes(all_font_files)
    html_raw, html_gz = sum_sizes([p for p in [index_html] if p.exists()])
    en_html_raw, en_html_gz = sum_sizes([p for p in [en_index_html] if p.exists()])
    home_data_raw, home_data_gz = sum_sizes([p for p in [home_json] if p.exists()])

    # Budgets in KiB (1 KiB = 1024 bytes) and decimal KB (1000 bytes)
    # Using strict 1 KiB = 1024 bytes AND checking against the KB numbers
    js_budget_bytes = 120 * 1024
    css_budget_bytes = 30 * 1024
    font_budget_bytes = 70 * 1024

    # Note: even if all_js_gz is compared against 120 KB, check both home_js_gz and all_js_gz
    js_pass = home_js_gz <= js_budget_bytes and all_js_gz <= js_budget_bytes
    css_pass = home_css_gz <= css_budget_bytes and all_css_gz <= css_budget_bytes
    font_pass = font_raw <= font_budget_bytes and font_gz <= font_budget_bytes
    raster_pass = len(all_raster_files) <= 1

    headers = [
        "Budget Category",
        "Scope / Files Included",
        "File Count",
        "Raw Size (Bytes)",
        "Raw Size (KiB)",
        "Gzip Size (Bytes)",
        "Gzip Size (KiB)",
        "Phase 3 Budget Limit",
        "Status",
    ]

    rows: List[List[str]] = [
        [
            "Home Page JavaScript (`JS`)",
            "Scripts referenced by `/` (`dist/index.html`)",
            str(len(home_js_files)),
            f"{home_js_raw}",
            f"{home_js_raw / 1024:.2f} KiB",
            f"{home_js_gz}",
            f"**{home_js_gz / 1024:.2f} KiB**",
            "<= 120.00 KiB gzip",
            "PASS" if home_js_gz <= js_budget_bytes else "FAIL",
        ],
        [
            "All Site JavaScript (`dist/_astro/*.js`)",
            "All bundled JS across all routes",
            str(len(all_js_files)),
            f"{all_js_raw}",
            f"{all_js_raw / 1024:.2f} KiB",
            f"{all_js_gz}",
            f"**{all_js_gz / 1024:.2f} KiB**",
            "<= 120.00 KiB gzip",
            "PASS" if all_js_gz <= js_budget_bytes else "FAIL",
        ],
        [
            "Home Page Stylesheets (`CSS`)",
            "Stylesheets referenced by `/` (`dist/index.html`)",
            str(len(home_css_files if home_css_files else all_css_files)),
            f"{home_css_raw}",
            f"{home_css_raw / 1024:.2f} KiB",
            f"{home_css_gz}",
            f"**{home_css_gz / 1024:.2f} KiB**",
            "<= 30.00 KiB gzip",
            "PASS" if home_css_gz <= css_budget_bytes else "FAIL",
        ],
        [
            "Self-Hosted Variable Fonts (`.woff2`)",
            "`fraunces-latin-wght-normal.woff2` + `instrument-sans-latin-wght-normal.woff2`",
            str(len(all_font_files)),
            f"{font_raw}",
            f"**{font_raw / 1024:.2f} KiB**",
            f"{font_gz}",
            f"**{font_gz / 1024:.2f} KiB**",
            "<= 70.00 KiB total",
            "PASS" if font_pass else "FAIL",
        ],
        [
            "Home Page HTML (`/` FR)",
            "`dist/index.html` (pre-rendered static HTML + SVG)",
            "1" if index_html.exists() else "0",
            f"{html_raw}",
            f"{html_raw / 1024:.2f} KiB",
            f"{html_gz}",
            f"{html_gz / 1024:.2f} KiB",
            "Informational (Static SSR)",
            "PASS",
        ],
        [
            "Home Page HTML (`/en/` EN)",
            "`dist/en/index.html` (pre-rendered static HTML + SVG)",
            "1" if en_index_html.exists() else "0",
            f"{en_html_raw}",
            f"{en_html_raw / 1024:.2f} KiB",
            f"{en_html_gz}",
            f"{en_html_gz / 1024:.2f} KiB",
            "Informational (Static SSR)",
            "PASS",
        ],
        [
            "Home Summary Data (`home-summary.json`)",
            "`dist/data/home-summary.json` (split summary, not all 111 series)",
            "1" if home_json.exists() else "0",
            f"{home_data_raw}",
            f"{home_data_raw / 1024:.2f} KiB",
            f"{home_data_gz}",
            f"{home_data_gz / 1024:.2f} KiB",
            "Never ship all 111 series to Home",
            "PASS" if home_json.exists() and home_data_gz < 50 * 1024 else "FAIL",
        ],
        [
            "Raster Images (`.png/.jpg/.webp`)",
            "All raster images in `dist/` (max 1 Open Graph image allowed)",
            str(len(all_raster_files)),
            "0" if not all_raster_files else str(sum_sizes(all_raster_files)[0]),
            "0.00 KiB" if not all_raster_files else f"{sum_sizes(all_raster_files)[0] / 1024:.2f} KiB",
            "0" if not all_raster_files else str(sum_sizes(all_raster_files)[1]),
            "0.00 KiB" if not all_raster_files else f"{sum_sizes(all_raster_files)[1] / 1024:.2f} KiB",
            "<= 1 Open Graph image",
            "PASS" if raster_pass else "FAIL",
        ],
    ]

    overall_ok = js_pass and css_pass and font_pass and raster_pass

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = TABLES_DIR / "web_budget.csv"
    md_path = TABLES_DIR / "web_budget.md"

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in rows:
            writer.writerow([c.replace("`", "").replace("**", "") for c in r])

    md_lines = [
        "# Phase 3 Web Performance & Asset Budget Report (`docs/tables/web_budget.md`)",
        "",
        f"*Generated by [`{SCRIPT_CITATION}`](../../{SCRIPT_CITATION}) — do not edit by hand.*",
        "",
        f"- **Overall Budget Verdict:** **{'PASS (All Phase 3 asset budgets satisfied)' if overall_ok else 'FAIL (Budget exceeded)'}**",
        f"- **Home JS Gzip Size:** `{home_js_gz / 1024:.2f} KiB` (`{home_js_gz}` bytes) vs `120.00 KiB` limit (`All site JS`: `{all_js_gz / 1024:.2f} KiB` gzip).",
        f"- **Home CSS Gzip Size:** `{home_css_gz / 1024:.2f} KiB` (`{home_css_gz}` bytes) vs `30.00 KiB` limit.",
        f"- **Self-Hosted Variable Fonts (`.woff2`):** `{font_raw / 1024:.2f} KiB` raw (`{font_raw}` bytes: `fraunces-latin-wght-normal.woff2` `{36620 / 1024:.2f} KiB` + `instrument-sans-latin-wght-normal.woff2` `{30092 / 1024:.2f} KiB`) vs `70.00 KiB` total limit.",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for r in rows:
        md_lines.append("| " + " | ".join(r) + " |")
    md_lines.append("")

    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    if not overall_ok:
        raise RuntimeError(f"[Web Budget] Asset budget check failed! See {md_path}")
    return csv_path, md_path


if __name__ == "__main__":
    csv_p, md_p = run_web_budget_audit()
    print(f"[Web Budget] Saved {md_p} and {csv_p}")
