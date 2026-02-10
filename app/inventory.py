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
    # safety: pastikan API key & spreadsheet id ada
    if not API_KEY or not SPREADSHEET_ID:
        raise RuntimeError(
            "GOOGLE_SHEETS_API_KEY atau SPREADSHEET_ID belum diset di .env"
        )

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

    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print("FETCH_INVENTORY: request error:", e)
        # jangan raise ke caller (agar bot tetap hidup) — kembalikan empty df
        return pd.DataFrame()

    values = res.json().get("values", [])
    if len(values) < 2:
        return pd.DataFrame()

    # INI
    raw_headers = values[0]
    # Normalisasi header: lowercase, ganti spasi dengan underscore
    headers = [
        h.strip().lower().replace(" ", "_") if h and str(h).strip() else f"col_{i}"
        for i, h in enumerate(raw_headers)
    ]

    df = pd.DataFrame(values[1:], columns=headers)

    # Hapus baris ini jika ada dua kali:
    # df.columns = [c.strip().lower() for c in df.columns]
    # Cukup pastikan baris di bawah ini yang aktif:
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # ===== KONVERSI & CLEAN HARGA =====
    if "harga" in df.columns:
        s = df["harga"].astype(str).fillna("")
        # hapus currency words like 'rp', 'idr' (case-insensitive)
        s = s.str.replace(r"(?i)rp|idr", "", regex=True).str.strip()
        # ganti koma/dot ribuan -> kosong
        s = s.str.replace(",", "", regex=False).str.replace(".", "", regex=False)
        # ubah trailing 'k' atau 'K' (contoh: 250k -> 250000)
        s = s.str.replace(r"(?i)\bk\b", "000", regex=True)
        # terakhir numeric
        df["harga"] = pd.to_numeric(s, errors="coerce")

    # ===== KONVERSI STOK =====
    if "stok" in df.columns:
        df["stok"] = pd.to_numeric(df["stok"], errors="coerce").fillna(0).astype(int)

    # ===== ALIAS: pastikan string dan lower (mudah match) =====
    if "alias" in df.columns:
        df["alias"] = df["alias"].fillna("").astype(str).str.lower().str.strip()

    # ===== UKURAN: bersihkan spasi, dan simpan apa adanya (upper/lower tidak dipaksakan) =====
    if "ukuran" in df.columns:
        df["ukuran"] = df["ukuran"].astype(str).str.strip()

    # ===== BERSIHKAN ROW MINIMAL =====
    # hanya drop rows jika kolom tersebut memang ada
    required_cols = [c for c in ["harga", "nama_produk"] if c in df.columns]
    if required_cols:
        df = df.dropna(subset=required_cols, how="any")

    # simpan cache
    _inventory_cache["data"] = df
    _inventory_cache["last_fetch"] = now

    # (opsional) debug kecil — hapus atau komentari saat sudah stable
    # print("DEBUG INVENTORY COLUMNS:", df.columns.tolist(), "ROWS:", len(df))

    return df


def get_all_aliases(df):
    """
    Ambil semua alias produk dari inventory.
    Return: list[str] (lowercase, bersih, unik)
    """
    if df is None or df.empty:
        return []

    if "alias" not in df.columns:
        return []

    aliases = set()

    for cell in df["alias"].dropna():
        # pastikan string
        text = str(cell).lower()

        # split multiple alias
        for a in text.split(","):
            alias = a.strip().replace("-", " ").replace("_", " ")

            # normalisasi spasi ganda
            alias = " ".join(alias.split())

            if alias and alias not in {"-", "n/a", "na"}:
                aliases.add(alias)

    return sorted(list(aliases))


def get_products_by_alias(df, alias_keyword: str):
    if df is None or df.empty:
        return df.iloc[0:0]

    if "alias" not in df.columns:
        return df.iloc[0:0]

    if not alias_keyword:
        return df.iloc[0:0]

    # normalisasi keyword user
    keyword = alias_keyword.lower().replace("-", " ").replace("_", " ")
    keyword = " ".join(keyword.split())

    def alias_match(cell):
        if not cell or pd.isna(cell):
            return False

        text = str(cell).lower().replace("-", " ").replace("_", " ")
        text = " ".join(text.split())

        # exact word match (lebih aman dari substring liar)
        return keyword in text

    mask = df["alias"].apply(alias_match)
    return df[mask]


def filter_by_criteria(gender=None, budget=None, size=None):
    """
    Filter inventory berdasarkan kriteria.
    TIDAK memfilter stok > 0 (biar logic.py yang tentukan ready / habis)
    """
    df = fetch_inventory()

    if df is None or df.empty:
        return df

    df = df.copy()

    # ===== NORMALISASI KOLOM =====
    for col in ["harga", "stok"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ===== FILTER UKURAN =====
    if size and "ukuran" in df.columns:
        df = df[df["ukuran"].astype(str).str.upper() == size.upper()]

    # ===== FILTER BUDGET =====
    if budget is not None and "harga" in df.columns:
        df = df[df["harga"].notna() & (df["harga"] <= budget)]

    # ===== FILTER GENDER =====
    if gender and "gender" in df.columns:
        df = df[df["gender"].astype(str).str.lower() == gender.lower()]

    return df
