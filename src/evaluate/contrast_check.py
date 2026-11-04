"""WCAG 2.1 AA contrast verification for all Phase 3 Bénin AgroMarket color token pairs.

Per `docs/PHASE3_BRIEF.md` and `AGENTS.md` (`## Numbers in documents`):
- Tokens: `ink #1E1B16`, `sand #F6F0E4`, `sand-2 #EDE3D0`, `laterite #B5471F`,
  `maize #E3A81F`, `green #2F5D3A`, `muted #6F665A`, `line #D9CDB8`.
- Maize yellow (`#E3A81F`) is never used for text on light backgrounds (`sand`, `sand-2`).
  Text on `maize` background is always `ink` (`#1E1B16`).
- Writes `docs/tables/contrast_check.{csv,md}` with exact relative luminance and contrast
  ratios (`(L1 + 0.05) / (L2 + 0.05)`) computed dynamically at runtime.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Tuple

from src.config import PROJECT_ROOT, TABLES_DIR

SCRIPT_CITATION = "src/evaluate/contrast_check.py"

TOKENS: Dict[str, str] = {
    "ink": "#1E1B16",
    "sand": "#F6F0E4",
    "sand-2": "#EDE3D0",
    "laterite": "#B5471F",
    "maize": "#E3A81F",
    "green": "#2F5D3A",
    "muted": "#6F665A",
    "line": "#D9CDB8",
    "paper-white": "#FFFDF9",
}


def hex_to_rgb01(hex_str: str) -> Tuple[float, float, float]:
    """Convert `#RRGGBB` hex string to normalized `(r, g, b)` in `[0, 1]`."""
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0)


def relative_luminance(hex_str: str) -> float:
    """Compute WCAG 2.1 relative luminance `L` for a `#RRGGBB` color."""
    def channel_lum(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = hex_to_rgb01(hex_str)
    return 0.2126 * channel_lum(r) + 0.7152 * channel_lum(g) + 0.0722 * channel_lum(b)


def contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """Compute WCAG 2.1 contrast ratio `(L_lighter + 0.05) / (L_darker + 0.05)`."""
    l1 = relative_luminance(fg_hex)
    l2 = relative_luminance(bg_hex)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def run_contrast_audit() -> Tuple[Path, Path]:
    """Verify WCAG AA contrast for every text/background and UI token pair."""
    r_ink_maize = contrast_ratio(TOKENS["ink"], TOKENS["maize"])
    r_lat_sand = contrast_ratio(TOKENS["laterite"], TOKENS["sand"])
    r_lat_paper = contrast_ratio(TOKENS["laterite"], TOKENS["paper-white"])
    r_lat_sand2 = contrast_ratio(TOKENS["laterite"], TOKENS["sand-2"])
    r_ink_sand2 = contrast_ratio(TOKENS["ink"], TOKENS["sand-2"])
    r_mut_sand = contrast_ratio(TOKENS["muted"], TOKENS["sand"])
    r_mut_sand2 = contrast_ratio(TOKENS["muted"], TOKENS["sand-2"])
    r_maize_sand = contrast_ratio(TOKENS["maize"], TOKENS["sand"])
    r_maize_sand2 = contrast_ratio(TOKENS["maize"], TOKENS["sand-2"])

    pairs_spec: List[Tuple[str, str, str, str]] = [
        ("ink", "sand", "Primary body & display text on primary page background", "Allowed (AAA)"),
        ("ink", "sand-2", "Primary text on cards, callouts, and table headers", "Allowed (AAA)"),
        ("ink", "paper-white", "Primary text on elevated chart/tooltip surface", "Allowed (AAA)"),
        ("ink", "line", "Primary text on subtle neutral badge/pill (`#D9CDB8`)", "Allowed (AAA)"),
        ("muted", "sand", "Secondary/caption/axis text on `sand` background", "Allowed (AA Normal & Large)"),
        (
            "muted",
            "sand-2",
            "Secondary text on `sand-2` surface",
            f"Large/UI text >=18.67px bold ({r_mut_sand2:.2f}:1 >= 3.0:1); use `ink` ({r_ink_sand2:.2f}:1) for small body text on `sand-2`",
        ),
        ("muted", "paper-white", "Secondary text inside chart tooltips/panels", "Allowed (AA Normal & Large)"),
        ("laterite", "sand", "Tomatoes accent / links / badges on `sand` background", "Allowed (AA Normal & Large)"),
        (
            "laterite",
            "sand-2",
            "Tomatoes accent on `sand-2` surface",
            f"Large/UI/Graphical >=3.0:1 ({r_lat_sand2:.2f}:1); use `ink` ({r_ink_sand2:.2f}:1) or solid `laterite` fill with `sand` text ({r_lat_sand:.2f}:1) for small text",
        ),
        ("green", "sand", "Yam (white) accent / calibrated badge text on `sand`", "Allowed (AA Normal & Large)"),
        ("green", "sand-2", "Yam (white) accent / calibrated badge text on `sand-2`", "Allowed (AA Normal & Large)"),
        ("ink", "maize", "Text on Maize (`#E3A81F`) chip / badge fill (Brief rule: text on maize is ink)", "Allowed (AAA — Mandatory rule for Maize)"),
        ("sand", "ink", "Inverted footer / dark button text (`sand` on `ink`)", "Allowed (AAA)"),
        ("sand-2", "ink", "Inverted secondary text (`sand-2` on `ink`)", "Allowed (AAA)"),
        ("maize", "ink", "Maize accent highlight on dark `ink` background", "Allowed (AAA on dark `ink` only)"),
        ("sand", "laterite", "Light `sand` text on solid `laterite` button/badge fill", "Allowed (AA Normal & Large)"),
        ("sand", "green", "Light `sand` text on solid `green` button/badge fill", "Allowed (AAA / AA Normal & Large)"),
        (
            "maize",
            "sand",
            "BANNED: Maize yellow text on light `sand` background",
            f"BANNED by brief ({r_maize_sand:.2f}:1 fails AA — never used for text on light backgrounds)",
        ),
        (
            "maize",
            "sand-2",
            "BANNED: Maize yellow text on light `sand-2` background",
            f"BANNED by brief ({r_maize_sand2:.2f}:1 fails AA — never used for text on light backgrounds)",
        ),
    ]

    headers = [
        "Pair ID",
        "Foreground Token",
        "Foreground Hex",
        "FG Luminance",
        "Background Token",
        "Background Hex",
        "BG Luminance",
        "Contrast Ratio",
        "WCAG AA Normal (>=4.5:1)",
        "WCAG AA Large/UI (>=3.0:1)",
        "Usage Role & Enforcement Verdict",
    ]
    rows: List[List[str]] = []

    for idx, (fg_name, bg_name, role, policy_note) in enumerate(pairs_spec, start=1):
        fg_hex = TOKENS[fg_name]
        bg_hex = TOKENS[bg_name]
        l_fg = relative_luminance(fg_hex)
        l_bg = relative_luminance(bg_hex)
        ratio = contrast_ratio(fg_hex, bg_hex)
        pass_aa_normal = (
            "PASS"
            if ratio >= 4.5
            else ("BANNED (Expected Fail)" if "BANNED" in role else "Large/UI Only (>=3.0:1)")
        )
        pass_aa_large = (
            "PASS"
            if ratio >= 3.0
            else ("BANNED (Expected Fail)" if "BANNED" in role else "FAIL")
        )

        rows.append([
            f"CLR-{idx:02d}",
            f"`{fg_name}`",
            f"`{fg_hex}`",
            f"{l_fg:.4f}",
            f"`{bg_name}`",
            f"`{bg_hex}`",
            f"{l_bg:.4f}",
            f"**{ratio:.2f}:1**",
            pass_aa_normal,
            pass_aa_large,
            f"{role} — {policy_note}",
        ])

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = TABLES_DIR / "contrast_check.csv"
    md_path = TABLES_DIR / "contrast_check.md"

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in rows:
            writer.writerow([c.replace("`", "").replace("**", "") for c in r])

    md_lines = [
        "# Phase 3 Design Token WCAG 2.1 Contrast Verification (`docs/tables/contrast_check.md`)",
        "",
        f"*Generated by [`{SCRIPT_CITATION}`](file://{PROJECT_ROOT / SCRIPT_CITATION}) — do not edit by hand.*",
        "",
        "- Verifies WCAG 2.1 relative luminance and contrast ratios for every text/background token pair defined in `docs/PHASE3_BRIEF.md`.",
        f"- Enforces the strict rule: **Maize yellow (`#E3A81F`) is never used for text on light backgrounds (`sand #F6F0E4` at `{r_maize_sand:.2f}:1`, `sand-2 #EDE3D0` at `{r_maize_sand2:.2f}:1`); text on `maize` is always `ink` (`#1E1B16`, `{r_ink_maize:.2f}:1` AAA)**.",
        f"- Note on `laterite` (`#B5471F`) and `muted` (`#6F665A`): both pass WCAG AA normal text (`>= 4.5:1`) on `sand` (`{r_lat_sand:.2f}:1` and `{r_mut_sand:.2f}:1`) and `paper-white` (`{r_lat_paper:.2f}:1`), and pass AA large text / UI components (`>= 3.0:1`) on `sand-2` (`{r_lat_sand2:.2f}:1` and `{r_mut_sand2:.2f}:1`). For small normal-weight text inside `sand-2` cards or badges, we use `ink` (`#1E1B16`, `{r_ink_sand2:.2f}:1`) or solid `laterite` fill with `sand` text (`{r_lat_sand:.2f}:1`).",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for r in rows:
        md_lines.append("| " + " | ".join(r) + " |")
    md_lines.append("")

    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return csv_path, md_path


if __name__ == "__main__":
    csv_p, md_p = run_contrast_audit()
    print(f"[Contrast Audit] Saved {md_p} and {csv_p}")
