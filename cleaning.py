import pandas as pd
from config import processed_path

def standardize_zillow(df: pd.DataFrame) -> pd.DataFrame:
    # Expect ZHVI-style format: RegionName (zip) + monthly date columns
    id_cols = [c for c in df.columns if not c[0].isdigit()]  # non-date columns
    value_cols = [c for c in df.columns if c not in id_cols]

    long_df = df.melt(
        id_vars=id_cols,
        value_vars=value_cols,
        var_name="date",
        value_name="price"
    )

    if "RegionName" in long_df.columns:
        long_df["zip"] = long_df["RegionName"].astype(str).str.zfill(5)
    else:
        long_df["zip"] = long_df["zip"].astype(str).str.zfill(5)

    long_df["date"] = pd.to_datetime(long_df["date"], errors="coerce")
    long_df = long_df.dropna(subset=["date", "price"])
    return long_df[["zip", "date", "price"]]


def standardize_redfin(df: pd.DataFrame) -> pd.DataFrame:
    # Flexible column mapping — adjust if your CSV schema differs
    date_cols = ["period_begin", "PERIOD_BEGIN", "date"]
    price_cols = ["median_sale_price", "MEDIAN_SALE_PRICE", "price", "price_numeric", "price_formatted"]
    zip_cols = ["region", "postal_code", "ZIP", "zip"]

    def pick(cols, candidates):
        for c in candidates:
            if c in cols:
                return c
        raise KeyError(f"None of {candidates} found in {cols}")

    date_col = pick(df.columns, date_cols)
    price_col = pick(df.columns, price_cols)
    zip_col = pick(df.columns, zip_cols)

    out = pd.DataFrame()
    out["zip"] = df[zip_col].astype(str).str.zfill(5)
    out["date"] = pd.to_datetime(df[date_col], errors="coerce")
    out["price"] = df[price_col]
    out = out.dropna(subset=["date", "price"])
    return out


def merge_sources(zillow_df: pd.DataFrame, redfin_df: pd.DataFrame) -> pd.DataFrame:
    z = standardize_zillow(zillow_df)
    r = standardize_redfin(redfin_df)
    combined = pd.concat([z, r], ignore_index=True)

    # Quarterly mean price per ZIP
    combined = (
        combined
        .set_index("date")
        .groupby("zip")
        .resample("Q")["price"]
        .mean()
        .reset_index()
    )

    fname = processed_path("merged_master.csv")
    combined.to_csv(fname, index=False)
    print(f"✅ Saved merged dataset: {fname}")
    return combined


if __name__ == "__main__":
    print("Run this by importing into a driver script after ingestion.")
