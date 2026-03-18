import time
import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_SHEETS_API_KEY")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

SHEET_STOK = "Stok"
SHEET_ORDERS = "Orders"
SHEET_PELANGGAN = "Pelanggan"

CACHE_TTL = 60
_stok_cache = {"data": None, "last_fetch": 0}

HARGA_DEFAULT_LPG = int(os.getenv("HARGA_LPG", "18000"))


# ===== FETCH STOK =====
def fetch_stok():
    if not API_KEY or not SPREADSHEET_ID:
        raise RuntimeError(
            "GOOGLE_SHEETS_API_KEY atau SPREADSHEET_ID belum diset di .env"
        )

    now = time.time()
    if _stok_cache["data"] is not None and now - _stok_cache["last_fetch"] < CACHE_TTL:
        return _stok_cache["data"]

    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/"
        f"{SPREADSHEET_ID}/values/{SHEET_STOK}?key={API_KEY}"
    )

    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print("FETCH_STOK ERROR:", e)
        return pd.DataFrame()

    values = res.json().get("values", [])
    if len(values) < 2:
        return pd.DataFrame()

    headers = [h.strip().lower().replace(" ", "_") for h in values[0]]
    df = pd.DataFrame(values[1:], columns=headers)

    for col in ["stok_awal", "terjual", "stok_sekarang", "batas_restock"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    _stok_cache["data"] = df
    _stok_cache["last_fetch"] = now
    return df


def get_stok_lpg() -> dict:
    """Return info stok LPG: stok, harga, tersedia, hampir_habis."""
    df = fetch_stok()
    if df.empty:
        return {
            "stok": 0,
            "harga": HARGA_DEFAULT_LPG,
            "tersedia": False,
            "hampir_habis": False,
        }

    mask = df["produk"].astype(str).str.lower().str.contains("lpg", na=False)
    row = df[mask]

    if row.empty:
        return {
            "stok": 0,
            "harga": HARGA_DEFAULT_LPG,
            "tersedia": False,
            "hampir_habis": False,
        }

    r = row.iloc[0]
    stok = int(r.get("stok_sekarang", r.get("stok_awal", 0)))
    batas = int(r.get("batas_restock", 10))

    return {
        "stok": stok,
        "harga": HARGA_DEFAULT_LPG,
        "tersedia": stok > 0,
        "hampir_habis": stok <= batas,
    }


def invalidate_stok_cache():
    _stok_cache["data"] = None
    _stok_cache["last_fetch"] = 0


# ===== GENERATE ORDER ID =====
def generate_order_id() -> str:
    try:
        url = (
            f"https://sheets.googleapis.com/v4/spreadsheets/"
            f"{SPREADSHEET_ID}/values/{SHEET_ORDERS}?key={API_KEY}"
        )
        res = requests.get(url, timeout=10)
        values = res.json().get("values", [])
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"ORD-{today}-"
        count = sum(1 for row in values[1:] if row and str(row[0]).startswith(prefix))
        return f"{prefix}{str(count + 1).zfill(3)}"
    except Exception:
        return f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"


# ===== CATAT ORDER =====
def catat_order(
    nama: str,
    no_wa: str,
    jumlah: int,
    metode_ambil: str = "Ambil Sendiri",
    catatan: str = "Tidak ada catatan",
    sumber: str = "WA Bot",
) -> dict:
    if not API_KEY or not SPREADSHEET_ID:
        return {"success": False, "order_id": "-", "total": 0}

    harga = HARGA_DEFAULT_LPG
    total = harga * jumlah
    order_id = generate_order_id()
    now = datetime.now()

    row = [
        order_id,
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M"),
        nama,
        no_wa,
        "LPG 3kg",
        jumlah,
        harga,
        total,
        metode_ambil,
        "Belum",  # Status_Bayar — ibu update manual
        catatan,
        sumber,
    ]

    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/"
        f"{SPREADSHEET_ID}/values/{SHEET_ORDERS}:append"
        f"?valueInputOption=USER_ENTERED&key={API_KEY}"
    )

    try:
        res = requests.post(url, json={"values": [row]}, timeout=10)
        res.raise_for_status()
        print(f"ORDER DICATAT: {order_id} | {nama} | {jumlah} tabung | Rp{total:,}")
        _update_pelanggan(nama, no_wa, total)
        invalidate_stok_cache()
        return {"success": True, "order_id": order_id, "total": total}
    except Exception as e:
        print("CATAT_ORDER ERROR:", e)
        return {"success": False, "order_id": order_id, "total": total}


# ===== UPDATE PELANGGAN =====
def _update_pelanggan(nama: str, no_wa: str, total_belanja: int):
    if not API_KEY or not SPREADSHEET_ID:
        return

    try:
        url_get = (
            f"https://sheets.googleapis.com/v4/spreadsheets/"
            f"{SPREADSHEET_ID}/values/{SHEET_PELANGGAN}?key={API_KEY}"
        )
        res = requests.get(url_get, timeout=10)
        values = res.json().get("values", [])
        today = datetime.now().strftime("%Y-%m-%d")
        no_wa_clean = str(no_wa).strip()

        existing_row = None
        existing_idx = None
        for i, row in enumerate(values[1:], start=2):
            if row and str(row[0]).strip() == no_wa_clean:
                existing_row = row
                existing_idx = i
                break

        if existing_row:
            total_order_lama = (
                int(existing_row[2]) if len(existing_row) > 2 and existing_row[2] else 0
            )
            total_belanja_lama = (
                int(existing_row[3]) if len(existing_row) > 3 and existing_row[3] else 0
            )
            total_order_baru = total_order_lama + 1
            total_belanja_baru = total_belanja_lama + total_belanja
            label = "Pelanggan Tetap" if total_order_baru >= 3 else "Pelanggan Baru"

            url_update = (
                f"https://sheets.googleapis.com/v4/spreadsheets/"
                f"{SPREADSHEET_ID}/values/{SHEET_PELANGGAN}"
                f"!C{existing_idx}:F{existing_idx}"
                f"?valueInputOption=USER_ENTERED&key={API_KEY}"
            )
            requests.put(
                url_update,
                json={"values": [[total_order_baru, total_belanja_baru, today, label]]},
                timeout=10,
            )
        else:
            url_append = (
                f"https://sheets.googleapis.com/v4/spreadsheets/"
                f"{SPREADSHEET_ID}/values/{SHEET_PELANGGAN}:append"
                f"?valueInputOption=USER_ENTERED&key={API_KEY}"
            )
            requests.post(
                url_append,
                json={
                    "values": [
                        [no_wa_clean, nama, 1, total_belanja, today, "Pelanggan Baru"]
                    ]
                },
                timeout=10,
            )
    except Exception as e:
        print("UPDATE_PELANGGAN ERROR:", e)
