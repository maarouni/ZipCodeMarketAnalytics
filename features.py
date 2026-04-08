import pandas as pd
from pathlib import Path
from config import processed_path


def load_merged() -> pd.DataFrame:
    """
    Load the merged master dataset produced by cleaning.merge_sources().
    Expected minimal schema: ['zip', 'date', 'price'].
    """
    fname = processed_path("merged_master.csv")
    if not fname.exists():
        raise FileNotFoundError(
            f"Expected {fname}. Run cleaning.merge_sources(...) first "
            "to create the merged dataset."
        )
    df = pd.read_csv(fname, dtype={'zip': str}, low_memory=False)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def _compute_volatility(df: pd.DataFrame) -> pd.Series:
    """
    Rolling Price Volatility (σ) per ZIP.

    For each ZIP:
      - sort by date
      - compute rolling 8-quarter (2-year) std/mean
      - assign that value to the corresponding row

    This makes volatility time-varying: early periods (fewer than 4 points)
    will be NaN; later periods stabilize.
    """
    if "price" not in df.columns:
        raise KeyError("Column 'price' missing from merged dataset.")

    # Work on a sorted copy to get correct rolling behavior
    df_sorted = df.sort_values(["zip", "date"])

    # Rolling 8 quarters with at least 4 data points
    roll = (
        df_sorted
        .groupby("zip")["price"]
        .rolling(window=8, min_periods=4)
    )

    vol = (roll.std() / roll.mean())
    # Clean up index from groupby+rolling
    vol = vol.reset_index(level=0, drop=True)
    vol.name = "volatility"

    # Align back to df_sorted, then to original index order
    vol = vol.reindex(df_sorted.index)
    return vol.sort_index()

def _compute_return_volatility(df: pd.DataFrame) -> pd.Series:
    """
    Financial Volatility (σ_returns) per ZIP.

    Measures the standard deviation of rolling percentage returns
    over an 8-quarter (2-year) window.

    This captures turbulence in BOTH:
      - downward periods (e.g., 2008–2010)
      - upward periods / run-ups (e.g., 2020–2022)

    σ_returns = std( pct_change(price) ) over rolling 8 quarters.
    """
    if "price" not in df.columns:
        raise KeyError("Column 'price' missing from merged dataset.")

    # Sort for proper rolling behavior
    df_sorted = df.sort_values(["zip", "date"])

    # Compute percentage returns per ZIP
    df_sorted["returns"] = df_sorted.groupby("zip")["price"].pct_change()

    # Rolling std of returns (8 quarters, need at least 4)
    vol_ret = (
        df_sorted
        .groupby("zip")["returns"]
        .rolling(window=8, min_periods=4)
        .std()
        .reset_index(level=0, drop=True)
    )

    vol_ret.name = "volatility_returns"

    # Align back to original index order
    vol_ret = vol_ret.reindex(df_sorted.index)
    return vol_ret.sort_index()

    

    # Clean up index from groupby+rolling
    vol = vol.reset_index(level=0, drop=True)
    vol.name = "volatility"

    # Align back to df_sorted, then to original index order
    vol = vol.reindex(df_sorted.index)
    return vol.sort_index()

def _compute_vacancy_rate(df: pd.DataFrame) -> pd.Series:
    """Vacancy Rate (%) = unsold / total_listings * 100."""
    if {"unsold", "total_listings"}.issubset(df.columns):
        vac = (df["unsold"] / df["total_listings"]) * 100
        return vac.clip(lower=0)
    else:
        return pd.Series([pd.NA] * len(df), index=df.index, name="vacancy_rate")


def _compute_rent_growth(df: pd.DataFrame) -> pd.Series:
    """Mean Rent Growth (%) = pct_change over 4 periods (quarters) if 'rent' exists."""
    if "rent" not in df.columns:
        return pd.Series([pd.NA] * len(df), index=df.index, name="rent_growth")

    df_sorted = df.sort_values(["zip", "date"])
    rg = df_sorted.groupby("zip")["rent"].pct_change(periods=4) * 100
    rg = rg.reindex(df_sorted.index)
    rg.name = "rent_growth"
    return rg.sort_index()


def _score_series(s: pd.Series, multiplier: float) -> pd.Series:
    """Normalize numeric feature into 0–100 range."""
    if s.isna().all():
        return pd.Series([pd.NA] * len(s), index=s.index)
    return (multiplier * s).clip(0, 100)


def _compute_risk_index(df: pd.DataFrame) -> pd.Series:
    """
    RiskIndex = 0.5 * VolatilityScore
              + 0.3 * VacancyScore
              + 0.2 * (100 - RentGrowthScore)
    """
    import numpy as np

    def row_risk(row):
        comps, wts = [], []
        if pd.notna(row.get("vol_score")):
            comps.append(row["vol_score"])
            wts.append(0.5)
        if pd.notna(row.get("vac_score")):
            comps.append(row["vac_score"])
            wts.append(0.3)
        if pd.notna(row.get("rent_score")):
            comps.append(100 - row["rent_score"])
            wts.append(0.2)
        if not comps:
            return np.nan
        ws = sum(wts)
        return sum(c * (w / ws) for c, w in zip(comps, wts))

    return df.apply(row_risk, axis=1)


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute volatility, vacancy, rent growth, and risk index."""
    df = df.copy()
    df = df.sort_values(["zip", "date"])

    # --- Volatility Metrics ---
    df["volatility"] = _compute_volatility(df)                  # Statistical σ (price-based)
    df["volatility_returns"] = _compute_return_volatility(df)   # Financial σ (returns-based)

    # --- Other Feature Metrics ---
    df["vacancy_rate"] = _compute_vacancy_rate(df)
    df["rent_growth"] = _compute_rent_growth(df)

    # --- Scoring ---
    df["vol_score"] = _score_series(df["volatility"], 200)
    df["vac_score"] = _score_series(df["vacancy_rate"], 10)
    df["rent_score"] = _score_series(df["rent_growth"], 20)

    # --- Risk Index ---
    df["risk_index"] = _compute_risk_index(df)
    return df

def run_feature_pipeline(save: bool = True) -> pd.DataFrame:
    """Run full feature engineering and optionally save to processed_data/features_master.csv."""
    merged = load_merged()
    features = compute_features(merged)

    if save:
        out_path = processed_path("features_master.csv")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        features.to_csv(out_path, index=False)
        print(f"✅ Saved features dataset to {out_path}")

    print("✅ Feature engineering complete. Sample:")
    print(features.head())
    return features


if __name__ == "__main__":
    run_feature_pipeline(save=True)
