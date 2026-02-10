import random
import re
from typing import Optional, List
import os
from dotenv import load_dotenv

load_dotenv()
# Ambil data dari .env
WA_ADMIN_NUMBER = os.getenv("WA_ADMIN_NUMBER", "6282135965079")
ADMIN_NEGO_MSG = os.getenv("ADMIN_NEGO_MESSAGE", "Halo Admin, mau nego harga ini")

# fungsi filter_by_criteria digunakan di beberapa flow (import awal)
from app.inventory import filter_by_criteria

# ===== MEMORY SESSION =====
session_store = {}

# ===== KEYWORDS =====
BUY_INTENT_KEYWORDS = [
    "beli",
    "checkout",
    "order",
    "pesan",
    "ambil",
    "jadi ambil",
    "mau yang",
    "mau ini",
    "yang ini aja",
    "yang itu aja",
    "cara beli",
    "gimana belinya",
    "gimana order",
    "bisa beli",
    "bisa order",
    "bisa pesan",
    "link dong",
    "linknya",
    "link checkout",
    "stoknya ada",
    "masih ada",
    "fix",
    "fix ambil",
    "gas",
    "gaskeun",
    "lanjut",
    "lanjut checkout",
    "aku mau",
    "saya mau",
    "deal",
    "oke ambil",
    "ambil yang",
]

RESET_KEYWORDS = [
    "reset",
    "ulang",
    "dari awal",
    "mulai lagi",
    "ganti",
    "ganti pilihan",
    "ubah pilihan",
    "cancel",
    "batal",
    "skip",
    "ngulang",
    "ulangin",
    "restart",
    "balik",
    "balik lagi",
    "salah",
    "keliru",
    "bingung",
    "ga jadi",
    "gak jadi",
]

GREETING_KEYWORDS = [
    "halo",
    "hai",
    "hi",
    "hello",
    "assalamualaikum",
    "pagi",
    "siang",
    "sore",
    "malam",
]

READY_KEYWORDS = [
    "ready",
    "stok ada",
    "stoknya",
    "masih ada",
    "ada gak",
    "ada ga",
    "ready tidak",
    "ready ga",
    "ready gak",
    "ready min?",
]

POST_CHECKOUT_KEYWORDS = [
    "oke",
    "ok",
    "siap",
    "ya",
    "iya",
    "yap",
    "gas",
    "bantuin",
    "bantu dong",
    "tolong bantu",
    "gimana caranya",
    "cara bayarnya",
    "bayarnya gimana",
    "bayar gimana",
    "transfer kemana",
    "bisa cod",
    "cod bisa",
    "rekening",
    "e-wallet",
    "ovo",
    "dana",
    "gopay",
    "shopeepay",
    "link error",
    "gak bisa",
    "kok error",
    "gagal",
    "checkout error",
]

# ===== VARIASI JAWABAN =====
ASK_GENDER_RESPONSES = [
    "Halo Kak 👋 Aku bantu carikan hoodie yang paling cocok ya 😊\nHoodie-nya buat cowok atau cewek?",
    "Hai Kak 😄 Lagi cari hoodie ya?\nBuat cowok atau cewek nih?",
    "Halo 👋 Biar makin pas, hoodie-nya buat cowok atau cewek ya Kak?",
    "Siap bantu Kak 😊 Hoodie-nya mau buat cowok atau cewek nih?",
]

ASK_BUDGET_RESPONSES = [
    "Siap Kak 😊 Budget Kakak di kisaran berapa nih?",
    "Oke Kak 👍 Boleh tahu budget-nya berapa?",
    "Siap 😄 Range harga yang Kakak inginkan berapa ya?",
    "Kak, budget-nya di angka berapa kira-kira? Biar aku pilihin yang paling pas 😊",
]

ASK_SIZE_RESPONSES = [
    "Oke Kak 👍 Ukuran Kakak apa ya? (S / M / L / XL)",
    "Siap 😊 Boleh info size-nya Kak? (S / M / L / XL)",
    "Biar makin pas, ukuran Kakak apa ya? (S / M / L / XL)",
    "Kak, size-nya berapa nih? (S / M / L / XL)",
]

FALLBACK_RESPONSES = [
    "Hehe 😅 Maaf Kak, aku belum nangkap maksudnya.\nBoleh kita lanjut dikit ya?",
    "Maaf Kak 🙏 Aku agak bingung.\nBoleh diulang sedikit?",
    "Hehe 😄 Kayaknya aku salah paham.\nKita lanjut dikit ya Kak.",
]

DETAIL_KEYWORDS = [
    "detail",
    "detail lengkap",
    "lihat detail",
    "info lengkap",
    "info detail",
    "tolong detail",
    "spek",
    "spesifikasi",
    "kondisi",
    "kondisi barang",
]

NEGO_KEYWORDS = [
    "nego",
    "boleh kurang",
    "diskon",
    "kurangin",
    "pasnya berapa",
    "bisa kurang",
    "harga net",
    "kurangi",
    "potongan",
    "minta diskon",
]


# ===== UTIL FUNCTIONS =====
def parse_budget(text: str) -> Optional[int]:
    text = text.lower().replace(" ", "")
    digits = "".join(filter(str.isdigit, text))
    if not digits:
        return None
    value = int(digits)
    if any(k in text for k in ["k", "rb", "ribu"]):
        value *= 1000
    return value


def parse_size(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"\b(XL|L|M|S)\b", text.upper())
    return m.group(1) if m else None


def parse_gender(text: str) -> Optional[str]:
    text = (text or "").lower()
    if any(k in text for k in ["cowok", "pria", "laki"]):
        return "cowok"
    if any(k in text for k in ["cewek", "wanita", "perempuan"]):
        return "cewek"
    return None


def extract_product_keyword(text: str, aliases: List[str]) -> Optional[str]:
    if not text:
        return None
    text = text.lower()
    for alias in aliases:
        alias = alias.strip().lower()
        if not alias:
            continue
        if f" {alias} " in f" {text} ":
            return alias
    return None


# ===== MAIN HANDLER =====
def handle_chat(message: str, session_id: Optional[str]):
    from app.inventory import fetch_inventory, get_all_aliases, get_products_by_alias

    if not session_id:
        session_id = "default"
    if session_id not in session_store:
        session_store[session_id] = {
            "state": "ask_gender",
            "gender": None,
            "budget": None,
            "size": None,
            "last_products": None,
        }

    session = session_store[session_id]
    message_lower = (message or "").lower().strip()

    # DEFINISIKAN 'state' DI AWAL agar tidak UnboundLocalError
    state = session.get("state")

    # 1. RESET & GREETING
    if any(k in message_lower for k in RESET_KEYWORDS):
        session_store[session_id] = {
            "state": "ask_gender",
            "gender": None,
            "budget": None,
            "size": None,
        }
        return random.choice(ASK_GENDER_RESPONSES)

    if any(k == message_lower for k in GREETING_KEYWORDS):
        return random.choice(ASK_GENDER_RESPONSES)

    # 2. LOGIKA NEGO (WA ADMIN) - Disatukan & Diperbaiki
    if any(k in message_lower for k in NEGO_KEYWORDS):
        session["state"] = "waiting_admin"

        # Ambil variabel global dengan benar
        global WA_ADMIN_NUMBER, ADMIN_NEGO_MSG

        encoded_msg = ADMIN_NEGO_MSG.replace(" ", "%20")
        link_wa = f"https://wa.me/{WA_ADMIN_NUMBER}?text={encoded_msg}"

        return (
            "Boleh banget nego Kak! 😍\n\n"
            "Tapi agar lebih enak bicaranya, langsung chat **Admin Pusat** kami ya. "
            "Beliau yang punya wewenang kasih harga spesial buat Kakak:\n\n"
            f"{link_wa}\n\n"
            "Klik link di atas untuk lanjut nego ya Kak! 🙏"
        )

    # ISI READY QUESTIONS

    # DETAIL HANDLER
    if any(k in message_lower for k in DETAIL_KEYWORDS):
        products = session.get("last_products")
        if products is not None and not products.empty:
            # --- PERBAIKAN: Cari produk spesifik yang disebut user ---
            selected_product = None
            for _, row in products.iterrows():
                # Cek apakah nama produk ada di dalam pesan user
                if row["nama_produk"].lower() in message_lower:
                    selected_product = row
                    break

            # Jika user tidak menyebut nama brand, ambil yang pertama (default)
            if selected_product is None:
                selected_product = products.iloc[0]

            p = selected_product
            session["state"] = "detail_shown"

            return (
                f"Siap Kak 😊 Ini detail lengkap hoodie **{p['nama_produk']}**:\n\n"
                f"• Kondisi: {p.get('deskripsi', '-')}\n"
                f"• Warna: {p.get('warna', '-')}\n"
                f"• Size: {p.get('ukuran', '-')}\n"
                f"• Stok: {int(p.get('stok', 0))} pcs\n"
                f"• Harga: Rp{int(p.get('harga', 0)):,}\n\n"
                "Kalau mau lanjut checkout atau mau nego, bilang aja ya Kak 😊"
            )

    # CHECKOUT HANDLER
    if session.get("state") in ["ready_shown", "detail_shown", "recommend"] and any(
        k in message_lower for k in BUY_INTENT_KEYWORDS
    ):
        products = session.get("last_products")
        if products is not None and not products.empty:
            p = products.iloc[0]
            session["state"] = "post_checkout"
            return (
                "Siap Kak 😍\nIni link checkout-nya ya:\n"
                f"{p.get('link_checkout','-')}\n\n"
                # "Kalau mau aku bantuin sampai beres juga bisa 😊"
            )

    # Logika ekstraksi informasi
    gender_guess = parse_gender(message_lower)
    budget_guess = parse_budget(message_lower)
    size_guess = parse_size(message)

    if gender_guess:
        session["gender"] = gender_guess
    if budget_guess:
        session["budget"] = budget_guess
    if size_guess:
        session["size"] = size_guess

    # --- LOGIKA TRANSISI: MENANGKAP PILIHAN PRODUK SETELAH REKOMENDASI ---
    df_inv = fetch_inventory()
    aliases = get_all_aliases(df_inv)
    product_keyword = next((a for a in aliases if a and a in message_lower), None)

    if product_keyword:
        products = get_products_by_alias(df_inv, product_keyword)
        if products.empty:
            return f"Maaf Kak 😢 Hoodie **{product_keyword.title()}** sedang kosong."

        total_stock = int(products["stok"].fillna(0).sum())
        if total_stock <= 0:
            return f"Maaf Kak 😢 Hoodie **{product_keyword.title()}** sedang habis."

        # Simpan ke session agar bisa lanjut ke detail/checkout
        session["state"] = "ready_shown"
        session["last_products"] = products

        # Ambil info untuk respon seragam
        sizes = sorted(products["ukuran"].astype(str).unique())
        price_min = int(products["harga"].min())

        # RESPON YANG BENAR (Disamakan dengan Ready Handler)
        return (
            f"Iya Kak 😊 Hoodie **{product_keyword.title()}** masih ready.\n\n"
            f"• Size tersedia: {', '.join(sizes)}\n"
            f"• Stok total: {total_stock} pcs\n"
            f"• Harga: Rp{price_min:,}\n\n"
            "Ketik *detail* kalau mau info lengkap, atau bilang *checkout* ya Kak 😊"
        )

    # --- CEK APAKAH SEMUA KRITERIA SUDAH TERPENUHI (Untuk Opsi 1) ---
    if session["gender"] and session["budget"] and session["size"]:
        products = filter_by_criteria(
            session["gender"], session["budget"], session["size"]
        )
        if products.empty:
            # Jika tidak ada hasil, tanya ulang kriteria tertentu
            session["budget"] = None
            session["state"] = "ask_budget"
            return "Waduh Kak 😢 Tidak ada yang cocok dengan kriteria itu. Mau coba budget atau ukuran lain?"

        session["state"] = "recommend"
        session["last_products"] = products
        res = "Siap Kak 😍 Ini yang paling cocok:\n\n"
        for _, row in products.iterrows():
            res += f"• {row['nama_produk']} (Size {row['ukuran']}) - Rp{int(row['harga']):,}\n"
        res += "\nMau checkout atau lihat detail yang mana Kak? 😊"
        return res

    # --- LOGIKA BERTATAHAP (Opsi 2) ---
    if not session["gender"]:
        session["state"] = "ask_gender"
        return random.choice(ASK_GENDER_RESPONSES)

    if not session["budget"]:
        session["state"] = "ask_budget"
        return random.choice(ASK_BUDGET_RESPONSES)

    if not session["size"]:
        session["state"] = "ask_size"
        return random.choice(ASK_SIZE_RESPONSES)

    return random.choice(FALLBACK_RESPONSES)
