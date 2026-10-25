"""Strictly causal feature engineering for Phase 2 rolling-origin forecasting.

Enforces:
- Safeguard 1 (No Leakage from Full-Sample Diagnostics): `robust_z`, `is_outlier_level`,
  `is_outlier_jump`, and `is_outlier` are explicitly banned from all feature matrices.
- Safeguard 2 (Ground-Truth Target Integrity): Only months with `is_observed == 1` are
  ever used as forecast targets (`target_y`). The 1-month interpolated column
  `price_interp_1m_max` (`is_imputed_1m == 1`) is never used as a forecast target, and
  is only used for lag construction in the explicitly labelled imputation-sensitivity
  variant (`use_interp_lags=True`).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.config import PROCESSED_DATA_DIR

BANNED_LEAKAGE_COLUMNS = frozenset({
    "robust_z",
    "is_outlier_level",
    "is_outlier_jump",
    "is_outlier",
    "outlier_reason",
})

BASE_FEATURE_COLS: List[str] = [
    "log_p_last",
    "months_since_obs",
    "log_p_lag1",
    "log_p_lag2",
    "log_p_lag3",
    "log_p_lag6",
    "log_p_lag11",
    "log_p_lag12",
    "log_p_target_lag12",
    "log_p_target_lag24",
    "mom_diff_1m",
    "yoy_diff_12m",
    "roll3_mean",
    "roll6_mean",
    "roll12_mean",
    "roll12_std",
    "dev_from_roll12",
    "mkt_expanding_mean",
    "mkt_expanding_median",
    "mkt_seasonal_idx_origin",
    "mkt_seasonal_idx_target",
    "zone_seasonal_idx_origin",
    "zone_seasonal_idx_target",
    "seasonal_log_ratio_target_vs_origin",
    "seasonal_anchor_pred",
    "sin_target_m1",
    "cos_target_m1",
    "sin_target_m2",
    "cos_target_m2",
    "sin_target_m3",
    "cos_target_m3",
    "latitude",
    "longitude",
    "zone_south",
    "zone_center",
    "zone_north",
]

WEATHER_FEATURE_COLS: List[str] = [
    "precip_lag1m",
    "precip_lag2m",
    "precip_lag3m",
    "precip_roll3m_lag1",
    "precip_anom_z_lag1m",
    "t2m_lag1m",
    "t2m_max_lag1m",
    "t2m_min_lag1m",
    "rh2m_lag1m",
]


def classify_agro_zone(lat: float) -> str:
    """Classify latitude into Benin's three agro-ecological zones."""
    if lat < 7.5:
        return "South (<7.5°N)"
    if lat < 9.5:
        return "Center (7.5°–9.5°N)"
    return "North (>=9.5°N)"


@dataclass
class PanelSeriesData:
    """Structured representation of the 93-month Tier-1 panel for a single product."""

    commodity: str
    product_slug: str
    dates: List[str]  # length T = 93 ('2019-01-15' .. '2026-09-15')
    year_months: List[str]  # length T = 93 ('2019-01' .. '2026-09')
    months: np.ndarray  # shape (T,), int 1..12
    markets: List[str]  # length M
    market_ids: List[str]  # length M
    admin1s: List[str]  # length M
    admin2s: List[str]  # length M
    latitudes: np.ndarray  # shape (M,)
    longitudes: np.ndarray  # shape (M,)
    zones: List[str]  # length M
    is_observed: np.ndarray  # shape (M, T), bool
    price_raw: np.ndarray  # shape (M, T), float (NaN when unobserved)
    log_price_raw: np.ndarray  # shape (M, T), float (NaN when unobserved)
    price_interp1m: np.ndarray  # shape (M, T), float (NaN when neither observed nor 1m-imputed)
    log_price_interp1m: np.ndarray  # shape (M, T), float
    is_imputed_1m: np.ndarray  # shape (M, T), bool
    weather_matrix: np.ndarray  # shape (M, T, len(WEATHER_FEATURE_COLS)), float


def load_product_panels(
    panel_path: Path = PROCESSED_DATA_DIR / "modeling_panel_2019_2026.csv",
) -> Dict[str, PanelSeriesData]:
    """Load `modeling_panel_2019_2026.csv` into structured per-product matrices.

    Explicitly strips diagnostic outlier columns (`Safeguard 1`) and keeps
    `is_observed == 1` ground-truth prices strictly separate from `price_interp_1m_max`
    (`Safeguard 2`).
    """
    df = pd.read_csv(panel_path, dtype={"market_id": str})

    # Safeguard 1 verification: drop full-sample outlier diagnostic columns immediately
    present_banned = [c for c in BANNED_LEAKAGE_COLUMNS if c in df.columns]
    if present_banned:
        df = df.drop(columns=present_banned)

    df = df.sort_values(["commodity", "market", "date"]).reset_index(drop=True)
    panels: Dict[str, PanelSeriesData] = {}

    for commodity, g_prod in df.groupby("commodity", sort=True):
        dates = sorted(g_prod["date"].unique().tolist())
        t_len = len(dates)
        date_to_idx = {d: i for i, d in enumerate(dates)}

        first_market_rows = g_prod[g_prod["market"] == g_prod["market"].iloc[0]].sort_values("date")
        year_months = first_market_rows["year_month"].tolist()
        months = first_market_rows["month"].to_numpy(dtype=int)
        product_slug = str(first_market_rows["product_slug"].iloc[0])

        markets = sorted(g_prod["market"].unique().tolist())
        m_len = len(markets)

        market_ids: List[str] = []
        admin1s: List[str] = []
        admin2s: List[str] = []
        latitudes = np.zeros(m_len, dtype=float)
        longitudes = np.zeros(m_len, dtype=float)
        zones: List[str] = []

        is_observed = np.zeros((m_len, t_len), dtype=bool)
        price_raw = np.full((m_len, t_len), np.nan, dtype=float)
        price_interp1m = np.full((m_len, t_len), np.nan, dtype=float)
        is_imputed_1m = np.zeros((m_len, t_len), dtype=bool)
        weather_matrix = np.full((m_len, t_len, len(WEATHER_FEATURE_COLS)), np.nan, dtype=float)

        for m_idx, (mkt, g_mkt) in enumerate(g_prod.groupby("market", sort=True)):
            g_mkt = g_mkt.sort_values("date")
            row0 = g_mkt.iloc[0]
            market_ids.append(str(row0["market_id"]))
            admin1s.append(str(row0["admin1"]))
            admin2s.append(str(row0["admin2"]))
            lat = float(row0["latitude"])
            lon = float(row0["longitude"])
            latitudes[m_idx] = lat
            longitudes[m_idx] = lon
            zones.append(classify_agro_zone(lat))

            t_indices = [date_to_idx[d] for d in g_mkt["date"]]
            obs_flags = g_mkt["is_observed"].to_numpy(dtype=int) == 1
            imp_flags = g_mkt["is_imputed_1m"].to_numpy(dtype=int) == 1
            p_raw = pd.to_numeric(g_mkt["price"], errors="coerce").to_numpy(dtype=float)
            p_int = pd.to_numeric(g_mkt["price_interp_1m_max"], errors="coerce").to_numpy(dtype=float)

            # Safeguard 2: raw price is only valid where is_observed == 1
            p_raw_clean = np.where(obs_flags, p_raw, np.nan)

            is_observed[m_idx, t_indices] = obs_flags
            is_imputed_1m[m_idx, t_indices] = imp_flags
            price_raw[m_idx, t_indices] = p_raw_clean
            price_interp1m[m_idx, t_indices] = p_int

            for w_idx, w_col in enumerate(WEATHER_FEATURE_COLS):
                weather_matrix[m_idx, t_indices, w_idx] = pd.to_numeric(
                    g_mkt[w_col], errors="coerce"
                ).to_numpy(dtype=float)

        panels[str(commodity)] = PanelSeriesData(
            commodity=str(commodity),
            product_slug=product_slug,
            dates=dates,
            year_months=year_months,
            months=months,
            markets=markets,
            market_ids=market_ids,
            admin1s=admin1s,
            admin2s=admin2s,
            latitudes=latitudes,
            longitudes=longitudes,
            zones=zones,
            is_observed=is_observed,
            price_raw=price_raw,
            log_price_raw=np.log(price_raw),
            price_interp1m=price_interp1m,
            log_price_interp1m=np.log(price_interp1m),
            is_imputed_1m=is_imputed_1m,
            weather_matrix=weather_matrix,
        )

    return panels


def compute_causal_seasonal_profiles(
    log_p_hist: np.ndarray,
    months_hist: np.ndarray,
    zones: List[str],
) -> Tuple[np.ndarray, Dict[str, np.ndarray], np.ndarray]:
    """Compute strictly causal detrended log-seasonal offsets up to current origin t.

    Parameters
    ----------
    log_p_hist : np.ndarray of shape (M, t+1)
        Historical log prices Strictly up to origin t (`0..t`).
    months_hist : np.ndarray of shape (t+1,)
        Calendar months (1..12) for indices `0..t`.
    zones : list of str, length M
        Agro-ecological zone per market.

    Returns
    -------
    mkt_seas : np.ndarray of shape (M, 13)
        Market-level additive log seasonal anomaly for months 1..12 (index 0 unused),
        shrunk toward the market's agro-ecological zone profile when a month has few obs.
    zone_seas : dict mapping zone -> np.ndarray of shape (13,)
        Zone-level additive log seasonal anomaly for months 1..12.
    nat_seas : np.ndarray of shape (13,)
        National product-wide additive log seasonal anomaly for months 1..12.
    """
    m_len, t_len = log_p_hist.shape
    # Causal centered/trailing 12m mean per market to remove secular trend without look-ahead:
    # For each tau in 0..t, subtract the mean of available observations in [max(0, tau-11)..tau]
    detrended = np.full_like(log_p_hist, np.nan)
    for tau in range(t_len):
        w_start = max(0, tau - 11)
        window = log_p_hist[:, w_start : tau + 1]
        cnt = np.sum(~np.isnan(window), axis=1)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            w_mean = np.nanmean(window, axis=1)
        valid = (cnt >= 3) & (~np.isnan(log_p_hist[:, tau]))
        detrended[valid, tau] = log_p_hist[valid, tau] - w_mean[valid]

    nat_seas = np.zeros(13, dtype=float)
    for cal_m in range(1, 13):
        cols = np.where(months_hist == cal_m)[0]
        if len(cols) > 0:
            vals = detrended[:, cols]
            if np.any(~np.isnan(vals)):
                nat_seas[cal_m] = float(np.nanmean(vals))
    nat_seas[1:] -= np.mean(nat_seas[1:])

    unique_zones = sorted(set(zones))
    zone_seas: Dict[str, np.ndarray] = {}
    for z in unique_zones:
        z_mask = np.array([zm == z for zm in zones], dtype=bool)
        z_arr = np.zeros(13, dtype=float)
        for cal_m in range(1, 13):
            cols = np.where(months_hist == cal_m)[0]
            if len(cols) > 0:
                vals = detrended[np.ix_(z_mask, cols)]
                n_v = int(np.sum(~np.isnan(vals)))
                if n_v > 0:
                    w = min(1.0, n_v / 6.0)
                    z_arr[cal_m] = w * float(np.nanmean(vals)) + (1.0 - w) * nat_seas[cal_m]
                else:
                    z_arr[cal_m] = nat_seas[cal_m]
            else:
                z_arr[cal_m] = nat_seas[cal_m]
        z_arr[1:] -= np.mean(z_arr[1:])
        zone_seas[z] = z_arr

    mkt_seas = np.zeros((m_len, 13), dtype=float)
    for m_idx in range(m_len):
        z_arr = zone_seas[zones[m_idx]]
        for cal_m in range(1, 13):
            cols = np.where(months_hist == cal_m)[0]
            if len(cols) > 0:
                vals = detrended[m_idx, cols]
                n_v = int(np.sum(~np.isnan(vals)))
                if n_v > 0:
                    w = min(1.0, n_v / 4.0)
                    mkt_seas[m_idx, cal_m] = w * float(np.nanmean(vals)) + (1.0 - w) * z_arr[cal_m]
                else:
                    mkt_seas[m_idx, cal_m] = z_arr[cal_m]
            else:
                mkt_seas[m_idx, cal_m] = z_arr[cal_m]
        mkt_seas[m_idx, 1:] -= np.mean(mkt_seas[m_idx, 1:])

    return mkt_seas, zone_seas, nat_seas


def build_features_at_origin(
    panel: PanelSeriesData,
    origin_idx: int,
    horizon: int,
    use_interp_lags: bool = False,
    precomputed_seas: Optional[Tuple[np.ndarray, Dict[str, np.ndarray], np.ndarray]] = None,
) -> np.ndarray:
    """Build feature matrix of shape (M, len(BASE_FEATURE_COLS) + len(WEATHER_FEATURE_COLS))
    for all M markets standing at `origin_idx` forecasting `origin_idx + horizon`.

    Strictly accesses only price/weather observations at indices `<= origin_idx`.
    """
    m_len = len(panel.markets)
    log_p_source = panel.log_price_interp1m if use_interp_lags else panel.log_price_raw
    log_p_hist = log_p_source[:, : origin_idx + 1]  # shape (M, origin_idx + 1)
    months_hist = panel.months[: origin_idx + 1]

    if precomputed_seas is None:
        mkt_seas, zone_seas, _ = compute_causal_seasonal_profiles(
            log_p_hist, months_hist, panel.zones
        )
    else:
        mkt_seas, zone_seas, _ = precomputed_seas

    origin_cal_month = int(panel.months[origin_idx])
    target_cal_month = int(((origin_cal_month - 1 + horizon) % 12) + 1)

    n_base = len(BASE_FEATURE_COLS)
    n_wea = len(WEATHER_FEATURE_COLS)
    X = np.full((m_len, n_base + n_wea), np.nan, dtype=float)

    def _get_lag(lag: int) -> np.ndarray:
        idx = origin_idx - lag
        if idx < 0:
            return np.full(m_len, np.nan, dtype=float)
        return log_p_hist[:, idx].copy()

    # Last observed log price at or before origin_idx and months_since_obs
    log_p_last = np.full(m_len, np.nan, dtype=float)
    months_since_obs = np.full(m_len, np.nan, dtype=float)
    last_obs_cal_month = np.full(m_len, origin_cal_month, dtype=int)
    for m_idx in range(m_len):
        valid_idxs = np.where(~np.isnan(log_p_hist[m_idx]))[0]
        if len(valid_idxs) > 0:
            last_i = int(valid_idxs[-1])
            log_p_last[m_idx] = log_p_hist[m_idx, last_i]
            months_since_obs[m_idx] = float(origin_idx - last_i)
            last_obs_cal_month[m_idx] = int(months_hist[last_i])

    log_p_lag1 = _get_lag(1)
    log_p_lag2 = _get_lag(2)
    log_p_lag3 = _get_lag(3)
    log_p_lag6 = _get_lag(6)
    log_p_lag11 = _get_lag(11)
    log_p_lag12 = _get_lag(12)

    # Target month 1 year ago (t + h - 12) and 2 years ago (t + h - 24)
    # Note: since h in {1, 2, 3}, t + h - 12 <= t - 9 < t, strictly causal!
    target_lag12_idx = origin_idx + horizon - 12
    target_lag24_idx = origin_idx + horizon - 24
    log_p_target_lag12 = (
        log_p_hist[:, target_lag12_idx].copy()
        if 0 <= target_lag12_idx <= origin_idx
        else np.full(m_len, np.nan, dtype=float)
    )
    log_p_target_lag24 = (
        log_p_hist[:, target_lag24_idx].copy()
        if 0 <= target_lag24_idx <= origin_idx
        else np.full(m_len, np.nan, dtype=float)
    )

    mom_diff_1m = log_p_last - log_p_lag1
    yoy_diff_12m = log_p_last - log_p_lag12

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        roll3_mean = np.nanmean(log_p_hist[:, max(0, origin_idx - 2) : origin_idx + 1], axis=1)
        roll6_mean = np.nanmean(log_p_hist[:, max(0, origin_idx - 5) : origin_idx + 1], axis=1)
        roll12_window = log_p_hist[:, max(0, origin_idx - 11) : origin_idx + 1]
        roll12_mean = np.nanmean(roll12_window, axis=1)
        roll12_std = np.nanstd(roll12_window, axis=1)
        mkt_expanding_mean = np.nanmean(log_p_hist, axis=1)
        mkt_expanding_median = np.nanmedian(log_p_hist, axis=1)

    dev_from_roll12 = log_p_last - roll12_mean

    mkt_seas_origin = np.array(
        [mkt_seas[m_idx, last_obs_cal_month[m_idx]] for m_idx in range(m_len)], dtype=float
    )
    mkt_seas_target = mkt_seas[:, target_cal_month].copy()
    zone_seas_origin = np.array(
        [zone_seas[panel.zones[m_idx]][last_obs_cal_month[m_idx]] for m_idx in range(m_len)],
        dtype=float,
    )
    zone_seas_target = np.array(
        [zone_seas[panel.zones[m_idx]][target_cal_month] for m_idx in range(m_len)], dtype=float
    )

    seasonal_log_ratio = mkt_seas_target - mkt_seas_origin
    # Local level anchor (blending last observed and 3m mean) + seasonal step
    local_anchor = np.where(~np.isnan(roll3_mean), 0.7 * log_p_last + 0.3 * roll3_mean, log_p_last)
    seasonal_anchor_pred = local_anchor + seasonal_log_ratio

    angle1 = 2.0 * np.pi * target_cal_month / 12.0
    angle2 = 4.0 * np.pi * target_cal_month / 12.0
    angle3 = 6.0 * np.pi * target_cal_month / 12.0

    zone_south = np.array([1.0 if z.startswith("South") else 0.0 for z in panel.zones])
    zone_center = np.array([1.0 if z.startswith("Center") else 0.0 for z in panel.zones])
    zone_north = np.array([1.0 if z.startswith("North") else 0.0 for z in panel.zones])

    base_arrays = [
        log_p_last,
        months_since_obs,
        log_p_lag1,
        log_p_lag2,
        log_p_lag3,
        log_p_lag6,
        log_p_lag11,
        log_p_lag12,
        log_p_target_lag12,
        log_p_target_lag24,
        mom_diff_1m,
        yoy_diff_12m,
        roll3_mean,
        roll6_mean,
        roll12_mean,
        roll12_std,
        dev_from_roll12,
        mkt_expanding_mean,
        mkt_expanding_median,
        mkt_seas_origin,
        mkt_seas_target,
        zone_seas_origin,
        zone_seas_target,
        seasonal_log_ratio,
        seasonal_anchor_pred,
        np.full(m_len, np.sin(angle1)),
        np.full(m_len, np.cos(angle1)),
        np.full(m_len, np.sin(angle2)),
        np.full(m_len, np.cos(angle2)),
        np.full(m_len, np.sin(angle3)),
        np.full(m_len, np.cos(angle3)),
        panel.latitudes,
        panel.longitudes,
        zone_south,
        zone_center,
        zone_north,
    ]

    for c_idx, arr in enumerate(base_arrays):
        X[:, c_idx] = arr

    # Weather features at origin_idx (strictly lagged relative to origin_idx)
    X[:, n_base:] = panel.weather_matrix[:, origin_idx, :]

    return X
