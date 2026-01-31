import time
import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_SHEETS_API_KEY")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = "Hoodie"  # ganti kalau nama sheet beda
CACHE_TTL = 60

_inventory_cache = {"data": None, "last_fetch": 0}


def fetch_inventory():
    now = time.time()
    if (
        _inventory_cache["data"] is not None
        and now - _inventory_cache["last_fetch"] < CACHE_TTL
    ):
        return _inventory_cache["data"]

    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/"
        f"{SPREADSHEET_ID}/values/{SHEET_NAME}?key={API_KEY}"
    )

    res = requests.get(url)
    res.raise_for_status()

    values = res.json().get("values", [])
    if not values:
        return pd.DataFrame()

    values = res.json().get("values", [])

    # safety check
    if len(values) < 2:
        return pd.DataFrame()

    raw_headers = values[0]

    # 🔥 FIX: pastikan header valid
    headers = [
        h.strip().lower().replace(" ", "_") if h.strip() != "" else f"col_{i}"
        for i, h in enumerate(raw_headers)
    ]

    rows = values[1:]

    df = pd.DataFrame(rows, columns=headers)

    # normalisasi kolom penting
    required_cols = ["harga", "stok", "ukuran"]

    for col in required_cols:
        if col not in df.columns:
            return pd.DataFrame()

    # Bersihkan & konversi harga
    df["harga"] = (
        df["harga"]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace("k", "000", regex=False)
        .str.replace("K", "000", regex=False)
    )
    df["harga"] = pd.to_numeric(df["harga"], errors="coerce")

    # Bersihkan & konversi stok
    df["stok"] = pd.to_numeric(df["stok"], errors="coerce")

    # Buang row invalid
    df = df.dropna(subset=["harga", "stok", "ukuran"])
    df = df[df["stok"] > 0]

    _inventory_cache["data"] = df
    _inventory_cache["last_fetch"] = now
    return df


def filter_by_criteria(gender, budget, size):
    df = fetch_inventory()

    if df.empty:
        return df

    df = df[df["stok"] > 0]
    df = df[df["ukuran"].str.upper() == size.upper()]
    df = df[df["harga"] <= budget]

    if "gender" in df.columns:
        df = df[df["gender"].str.lower() == gender.lower()]

    return df
