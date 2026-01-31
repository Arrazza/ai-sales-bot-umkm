import random
from typing import Optional
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
    "ready",
    "ready stock",
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


# ===== UTIL FUNCTIONS =====
def parse_budget(text: str) -> Optional[int]:
    text = text.lower().replace(" ", "")
    digits = "".join(filter(str.isdigit, text))
    if not digits:
        return None
    value = int(digits)
    if "k" in text or "rb" in text or "ribu" in text:
        value *= 1000
    return value


def parse_size(text: str) -> Optional[str]:
    text = text.upper()
    for size in ["S", "M", "L", "XL"]:
        if size in text.split():
            return size
    return None


def parse_gender(text: str) -> Optional[str]:
    text = text.lower()
    if "cowok" in text or "pria" in text or "laki" in text:
        return "cowok"
    if "cewek" in text or "wanita" in text or "perempuan" in text:
        return "cewek"
    return None


# ===== MAIN HANDLER =====
def handle_chat(message: str, session_id: Optional[str]):
    if not session_id:
        session_id = "default"

    message_lower = message.lower().strip()

    # Buat session baru kalau belum ada
    if session_id not in session_store:
        session_store[session_id] = {
            "state": "ask_gender",
            "gender": None,
            "budget": None,
            "size": None,
            "last_products": None,
        }

    session = session_store[session_id]

    # ===== RESET COMMAND =====
    if any(k in message_lower for k in RESET_KEYWORDS):
        session_store.pop(session_id, None)
        return random.choice(ASK_GENDER_RESPONSES)

    # ===== GREETING HANDLER =====
    if any(k == message_lower for k in GREETING_KEYWORDS):
        session["state"] = "ask_gender"
        return random.choice(ASK_GENDER_RESPONSES)

    # ===== MULTI-INTENT PRIORITY HANDLER =====
    gender_guess = parse_gender(message_lower)
    budget_guess = parse_budget(message_lower)
    size_guess = parse_size(message)

    if gender_guess and session["gender"] is None:
        session["gender"] = gender_guess

    if budget_guess and session["budget"] is None:
        session["budget"] = budget_guess

    if size_guess and session["size"] is None:
        session["size"] = size_guess

    if any([gender_guess, budget_guess, size_guess]):

        if session["gender"] is None:
            session["state"] = "ask_gender"
            return random.choice(ASK_GENDER_RESPONSES)

        if session["budget"] is None:
            session["state"] = "ask_budget"
            return random.choice(ASK_BUDGET_RESPONSES)

        if session["size"] is None:
            session["state"] = "ask_size"
            return random.choice(ASK_SIZE_RESPONSES)

        # 🔥 LANGSUNG REKOMENDASI
        products = filter_by_criteria(
            session["gender"], session["budget"], session["size"]
        )

        if products.empty:
            session["state"] = "ask_budget"
            return (
                "Waduh Kak 😢\n"
                "Tidak ada hoodie yang cocok dengan pilihan Kakak.\n"
                "Mau coba budget atau ukuran lain?"
            )

        session["state"] = "recommend"
        session["last_products"] = products

        response = "Siap Kak 😍\nIni hoodie yang paling cocok buat Kakak:\n\n"

        for _, row in products.iterrows():
            response += (
                f"• {row['nama_produk']} — Rp{int(row['harga']):,}\n"
                f"  Warna: {row['warna']} | Size: {row['ukuran']} | Stok: {row['stok']}\n"
                f"  Link: {row['link_checkout']}\n\n"
            )

        response += "Mau langsung checkout salah satunya Kak? 😊"
        return response

    # ===== DETEKSI NIAT BELI =====
    if session.get("last_products") is not None:

        if any(k in message_lower for k in BUY_INTENT_KEYWORDS):
            first = session["last_products"].iloc[0]
            session["state"] = "post_checkout"
            return (
                "Siap Kak 😍\n"
                "Ini link checkout-nya ya:\n"
                f"{first['link_checkout']}\n\n"
                "Kalau mau aku bantuin sampai beres juga bisa 😊"
            )

        if session["state"] == "post_checkout" and any(
            k in message_lower for k in POST_CHECKOUT_KEYWORDS
        ):
            return (
                "Siap Kak 😊\n"
                "Tinggal klik link tadi ya.\n\n"
                "Di halaman checkout nanti Kakak bisa pilih:\n"
                "• Transfer bank\n"
                "• E-wallet (OVO / DANA / GoPay)\n"
                "• COD (kalau tersedia)\n\n"
                "Kalau ada kendala di proses checkout,\n"
                "tinggal bilang aja ya Kak, aku bantu cekin 😄"
            )

    # ===== STATE MACHINE =====
    state = session["state"]

    if state == "ask_gender":
        gender = parse_gender(message_lower)

        if gender:
            session["gender"] = gender
            session["state"] = "ask_budget"
            return random.choice(ASK_BUDGET_RESPONSES)

        return random.choice(ASK_GENDER_RESPONSES)

    if state == "ask_budget":
        budget = parse_budget(message_lower)

        if budget:
            session["budget"] = budget
            session["state"] = "ask_size"
            return random.choice(ASK_SIZE_RESPONSES)

        return random.choice(ASK_BUDGET_RESPONSES)

    if state == "ask_size":
        size = parse_size(message)

        if size:
            session["size"] = size

            products = filter_by_criteria(
                session["gender"], session["budget"], session["size"]
            )

            if products.empty:
                session["state"] = "ask_budget"
                return (
                    "Waduh Kak 😢\n"
                    "Tidak ada hoodie yang cocok dengan pilihan Kakak.\n"
                    "Mau coba budget atau ukuran lain?"
                )

            session["state"] = "recommend"
            session["last_products"] = products

            response = "Siap Kak 😍\nIni hoodie yang paling cocok buat Kakak:\n\n"

            for _, row in products.iterrows():
                response += (
                    f"• {row['nama_produk']} — Rp{int(row['harga']):,}\n"
                    f"  Warna: {row['warna']} | Size: {row['ukuran']} | Stok: {row['stok']}\n"
                    f"  Link: {row['link_checkout']}\n\n"
                )

            response += "Mau langsung checkout salah satunya Kak? 😊"
            return response

        return random.choice(ASK_SIZE_RESPONSES)

    return random.choice(FALLBACK_RESPONSES)
