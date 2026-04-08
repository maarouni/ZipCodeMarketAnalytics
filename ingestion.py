import io
import zipfile
import requests
import pandas as pd
from datetime import datetime
from config import raw_path

def _timestamp():
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

def ingest_zillow_zhvi():
    """
    Example: Download a ZHVI CSV from Zillow Research.
    Update 'url' to the specific ZHVI file you want (metro, county, zip, etc.).
    """
    url = "https://files.zillowstatic.com/research/public_csvs/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
    resp = requests.get(url)
    resp.raise_for_status()

    fname = raw_path("zillow", f"zillow_zhvi_{_timestamp()}.csv")
    fname.parent.mkdir(parents=True, exist_ok=True)
    with open(fname, "wb") as f:
        f.write(resp.content)

    df = pd.read_csv(fname)
    return df

def ingest_redfin_local(csv_path: str):
    """
    Use this if you manually download from Redfin Data Center and place into raw_data/redfin.
    """
    df = pd.read_csv(csv_path)
    return df

def ingest_redfin_example():
    """
    Load manually downloaded Redfin TSV (UTF-16).
    Keeps both formatted and numeric prices for clarity.
    """

    from pathlib import Path
    import pandas as pd

    fname = raw_path("redfin", "redfin_sample.csv")
    if not fname.exists():
        raise FileNotFoundError(
            f"Expected {fname}. Download from Redfin Data Center and save there."
        )

    # --- Step 1: Read file safely ---
    df = pd.read_csv(fname, sep="\t", encoding="utf-16", low_memory=False)
    print(f"✅ Loaded Redfin file with {len(df):,} rows")

    # --- Step 2: Rename key columns ---
    rename_map = {
        "Region": "zip",
        "Month of Period End": "date",
        "Median Sale Price": "price_formatted"
    }
    for old, new in rename_map.items():
        if old not in df.columns:
            raise KeyError(f"Missing expected column: {old}")
    df = df.rename(columns=rename_map)[["zip", "date", "price_formatted"]]

    # --- Step 3: Clean up formatting & create numeric column ---
    def to_number(x):
        if isinstance(x, str):
            x = x.replace("$", "").replace(",", "").strip()
            if "K" in x:
                return float(x.replace("K", "")) * 1_000
            if "M" in x:
                return float(x.replace("M", "")) * 1_000_000
        try:
            return float(x)
        except:
            return None

    df["price_numeric"] = df["price_formatted"].apply(to_number)
    df = df.dropna(subset=["price_numeric"])

    print(f"✅ Cleaned Redfin dataset: {df.shape[0]:,} rows × {df.shape[1]} cols")
    print(df.head(5))
    return df

def run_basic_ingestion():
    print("Ingesting Zillow ZHVI...")
    zillow_df = ingest_zillow_zhvi()
    print(f"Zillow rows: {len(zillow_df)}")

    print("Loading Redfin sample...")
    redfin_df = ingest_redfin_example()
    print(f"Redfin rows: {len(redfin_df)}")

    return zillow_df, redfin_df

if __name__ == "__main__":
    run_basic_ingestion()
