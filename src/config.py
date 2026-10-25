"""Central configuration for Bénin AgroMarket data, cleaning, and modeling pipelines.

All product definitions, unit/price-type filters, temporal regime boundaries,
market tier thresholds, and filesystem paths live in this module so that adding
or toggling a commodity requires only a configuration change.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
RAW_DIR: Path = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR: Path = PROJECT_ROOT / "data" / "processed"
DOCS_DIR: Path = PROJECT_ROOT / "docs"
DOCS_TABLES_DIR: Path = DOCS_DIR / "tables"
DOCS_FIGURES_DIR: Path = DOCS_DIR / "figures"

WFP_PRICES_RAW_CSV: Path = RAW_DIR / "wfp_food_prices_ben.csv"
WFP_MARKETS_RAW_CSV: Path = RAW_DIR / "wfp_markets_ben.csv"
NASA_POWER_RAW_CSV: Path = RAW_DIR / "nasa_power_benin_markets.csv"

CLEANED_PRICES_ALL_CSV: Path = PROCESSED_DIR / "prices_cleaned_all.csv"
MODELING_PANEL_CSV: Path = PROCESSED_DIR / "modeling_panel_2019_2026.csv"
ACTIVE_MARKETS_CSV: Path = PROCESSED_DIR / "markets_active.csv"

RANDOM_SEED: int = 42

# Temporal boundaries and market coverage tier thresholds
MODELING_START_DATE: str = "2019-01-15"
MODELING_END_DATE: str = "2026-09-15"
MODELING_START_YM: str = "2019-01"
MODELING_END_YM: str = "2026-09"
MODELING_TOTAL_MONTHS: int = 93
HIATUS_YEARS: tuple[int, ...] = (2017, 2018)

TIER1_MIN_OBSERVED_MONTHS: int = 80  # >= 86.0% completeness over 93 months
TIER2_MIN_OBSERVED_MONTHS: int = 60  # >= 64.5% completeness over 93 months

# Standard filters
DEFAULT_PRICETYPE: str = "Retail"
DEFAULT_UNIT: str = "KG"
DEFAULT_CURRENCY: str = "XOF"
DEFAULT_PRICEFLAG: str = "actual"

# Outlier detection thresholds (flag-only, never delete)
OUTLIER_ROBUST_Z_THRESHOLD: float = 3.5
OUTLIER_MOM_LOG_JUMP_THRESHOLD: float = 0.6931471805599453  # ln(2.0): >=2x or <=0.5x in 1 month

# NASA POWER Agroclimatology API configuration
NASA_POWER_MONTHLY_URL: str = "https://power.larc.nasa.gov/api/temporal/monthly/point"
NASA_POWER_COMMUNITY: str = "AG"
NASA_POWER_PARAMETERS: tuple[str, ...] = (
    "PRECTOTCORR",
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "RH2M",
)
NASA_POWER_START_YEAR: int = 2006
NASA_POWER_END_YEAR: int = 2026
# MERRA-2 grid resolution is 0.5 deg lat x 0.625 deg lon
NASA_GRID_LAT_STEP: float = 0.5
NASA_GRID_LON_STEP: float = 0.625

ProductRole = Literal["forecast_primary", "exploration_only", "candidate_benchmark"]


@dataclass(frozen=True)
class ProductConfig:
    """Configuration for a tracked or candidate agricultural commodity in Benin."""

    slug: str
    commodity: str
    label_fr: str
    label_en: str
    category: str
    pricetype: str = DEFAULT_PRICETYPE
    unit: str = DEFAULT_UNIT
    currency: str = DEFAULT_CURRENCY
    priceflag: str = DEFAULT_PRICEFLAG
    role: ProductRole = "forecast_primary"
    enabled_in_pipeline: bool = True


PRODUCTS: tuple[ProductConfig, ...] = (
    ProductConfig(
        slug="maize_white",
        commodity="Maize (white)",
        label_fr="Maïs blanc",
        label_en="White Maize",
        category="cereals and tubers",
        role="forecast_primary",
        enabled_in_pipeline=True,
    ),
    ProductConfig(
        slug="tomatoes",
        commodity="Tomatoes",
        label_fr="Tomate fraîche",
        label_en="Fresh Tomato",
        category="vegetables and fruits",
        role="forecast_primary",
        enabled_in_pipeline=True,
    ),
    ProductConfig(
        slug="yam_white",
        commodity="Yam (white)",
        label_fr="Igname blanche (Kokoro)",
        label_en="White Yam (Kokoro)",
        category="cereals and tubers",
        role="forecast_primary",
        enabled_in_pipeline=True,
    ),
    ProductConfig(
        slug="yam_early",
        commodity="Yam",
        label_fr="Igname précoce (Laboko)",
        label_en="Early Yam (Laboko)",
        category="cereals and tubers",
        role="exploration_only",
        enabled_in_pipeline=True,
    ),
    # Candidate / benchmark products (out of primary scope; flip enabled_in_pipeline=True to include)
    ProductConfig(
        slug="cassava_gari",
        commodity="Cassava meal (gari)",
        label_fr="Gari (farine de manioc)",
        label_en="Cassava Meal (Gari)",
        category="cereals and tubers",
        role="candidate_benchmark",
        enabled_in_pipeline=False,
    ),
    ProductConfig(
        slug="rice_imported",
        commodity="Rice (imported)",
        label_fr="Riz importé",
        label_en="Imported Rice",
        category="cereals and tubers",
        role="candidate_benchmark",
        enabled_in_pipeline=False,
    ),
    ProductConfig(
        slug="beans_white",
        commodity="Beans (white)",
        label_fr="Niébé blanc (Haricot)",
        label_en="White Cowpeas (Beans)",
        category="pulses and nuts",
        role="candidate_benchmark",
        enabled_in_pipeline=False,
    ),
    ProductConfig(
        slug="sorghum_red",
        commodity="Sorghum (red)",
        label_fr="Sorgho rouge",
        label_en="Red Sorghum",
        category="cereals and tubers",
        role="candidate_benchmark",
        enabled_in_pipeline=False,
    ),
    ProductConfig(
        slug="sorghum_white",
        commodity="Sorghum",
        label_fr="Sorgho blanc",
        label_en="Sorghum",
        category="cereals and tubers",
        role="candidate_benchmark",
        enabled_in_pipeline=False,
    ),
    ProductConfig(
        slug="onions",
        commodity="Onions",
        label_fr="Oignon",
        label_en="Onions",
        category="vegetables and fruits",
        role="candidate_benchmark",
        enabled_in_pipeline=False,
    ),
)

ENABLED_PRODUCTS: tuple[ProductConfig, ...] = tuple(
    p for p in PRODUCTS if p.enabled_in_pipeline
)
FORECAST_PRIMARY_PRODUCTS: tuple[ProductConfig, ...] = tuple(
    p for p in PRODUCTS if p.enabled_in_pipeline and p.role == "forecast_primary"
)
PRODUCT_BY_COMMODITY: dict[str, ProductConfig] = {p.commodity: p for p in PRODUCTS}


def classify_market_tier(observed_months_2019_2026: int) -> str:
    """Classify a market into Tier-1, Tier-2, or Thin based on 2019-2026 observed months."""
    if observed_months_2019_2026 >= TIER1_MIN_OBSERVED_MONTHS:
        return "Tier-1 (>=80m)"
    if observed_months_2019_2026 >= TIER2_MIN_OBSERVED_MONTHS:
        return "Tier-2 (60-79m)"
    return "Thin (<60m)"
