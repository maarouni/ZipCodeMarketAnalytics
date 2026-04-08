import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Load .env
load_dotenv(BASE_DIR / ".env")

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

# Folders
RAW_DATA_DIR = BASE_DIR / "raw_data"
PROCESSED_DATA_DIR = BASE_DIR / "processed_data"
REPORTS_DIR = BASE_DIR / "reports"

for d in [RAW_DATA_DIR, PROCESSED_DATA_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def raw_path(*parts) -> Path:
    p = RAW_DATA_DIR.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def processed_path(*parts) -> Path:
    p = PROCESSED_DATA_DIR.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
