import random
import re
import os
import anthropic
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

WA_ADMIN_NUMBER = os.getenv("WA_ADMIN_NUMBER", "6282135965079")
NAMA_TOKO = "Wijaya Store"

# ===== SESSION STORE =====
session_store = {}

# ===== KEYWORDS =====
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
    "p",
]

STOK_KEYWORDS = [
    "stok",
    "masih ada",
    "ada gas",
    "ada gak",
    "ready",
    "tersedia",
    "ketersediaan",
    "habis",
]

ORDER_KEYWORDS = [
    "pesan",
    "order",
    "beli",
    "mau",
    "ambil",
    "minta",
    "butuh",
    "gas dong",
    "beli gas",
    "pesan gas",
]

JUMLAH_KEYWORDS = [
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "satu",
    "dua",
    "tiga",
    "empat",
    "lima",
]

METODE_ANTAR = ["antar", "diantar", "kirim", "delivery", "antarkan"]
METODE_AMBIL = ["ambil", "ambil sendiri", "kesini", "ke toko", "datang"]

KONFIRMASI_KEYWORDS = [
    "iya",
    "ya",
    "yap",
    "yes",
    "oke",
    "ok",
    "siap",
    "lanjut",
    "jadi",
    "konfirmasi",
    "benar",
    "betul",
]
BATAL_KEYWORDS = ["batal", "cancel", "tidak", "gak jadi", "ga jadi", "nope"]

RESET_KEYWORDS = ["reset", "ulang", "mulai lagi", "dari awal", "restart"]

FALLBACK_RESPONSES = [
    "Maaf kak, saya kurang paham maksudnya 😅 Bisa diulang ya?",
    "Hmm, saya belum nangkap nih 🙏 Boleh jelaskan lagi?",
]


# ===== PARSE JUMLAH =====
def parse_jumlah(text: str) -> Optional[int]:
    """Ekstrak jumlah tabung dari teks."""
    text = text.lower().strip()

    kata_angka = {
        "satu": 1,
        "dua": 2,
        "tiga": 3,
        "empat": 4,
        "lima": 5,
        "enam": 6,
        "tujuh": 7,
        "delapan": 8,
        "sembilan": 9,
        "sepuluh": 10,
    }
    for kata, angka in kata_angka.items():
        if kata in text:
            return angka

    # Cari angka di teks
    m = re.search(r"\b(\d+)\b", text)
    if m:
        val = int(m.group(1))
        if 1 <= val <= 50:  # sanity check
            return val
    return None


def parse_nama(text: str) -> Optional[str]:
    """Ekstrak nama dari teks seperti 'nama saya Budi' atau 'saya Budi'."""
    text = text.strip()
    patterns = [
        r"(?:nama saya|nama:?|saya|panggil saya|ini)\s+([A-Za-z\s]{2,30})",
        r"^([A-Za-z\s]{2,25})$",  # jika hanya nama saja
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            nama = m.group(1).strip().title()
            # Filter kata-kata yang bukan nama
            skip = ["iya", "ya", "ok", "oke", "siap", "halo", "hai", "mau", "minta"]
            if nama.lower() not in skip and len(nama) >= 2:
                return nama
    return None


# ===== AI FALLBACK =====
def get_ai_fallback(message: str, session: dict) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return random.choice(FALLBACK_RESPONSES)

    state = session.get("state", "greet")
    nama = session.get("nama", "Pelanggan")

    system_prompt = (
        f"Kamu adalah asisten AI dengan nama Arza {NAMA_TOKO}, toko penjual LPG 3kg di Klaten, Jawa Tengah. "
        "Kamu ramah, singkat, dan menggunakan bahasa Indonesia santai. "
        "Tugasmu membantu pelanggan cek stok dan pesan LPG 3kg. "
        "Harga LPG 3kg sekitar Rp18.000 per tabung. "
        "Jangan keluar dari konteks toko. Gunakan emoji secukupnya. Maksimal 3 kalimat. "
        f"Nama pelanggan: {nama}. Tahap percakapan saat ini: {state}."
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            system=system_prompt,
            messages=[{"role": "user", "content": message}],
        )
        return response.content[0].text.strip()
    except Exception:
        return random.choice(FALLBACK_RESPONSES)


# ===== RESET SESSION =====
def reset_session(session_id: str):
    session_store[session_id] = {
        "state": "greet",
        "nama": None,
        "no_wa": None,
        "jumlah": None,
        "metode": None,
        "catatan": None,
        "order_result": None,
    }
    return session_store[session_id]


# ===== MAIN HANDLER =====
def handle_chat(message: str, session_id: Optional[str], no_wa: Optional[str] = None):
    from app.inventory import get_stok_lpg, catat_order

    if not session_id:
        session_id = "default"
    if session_id not in session_store:
        reset_session(session_id)

    session = session_store[session_id]
    msg = (message or "").strip()
    msg_lower = msg.lower()

    # Simpan no_wa dari Fonnte jika ada
    if no_wa and not session.get("no_wa"):
        session["no_wa"] = no_wa

    # ===== RESET =====
    if any(k in msg_lower for k in RESET_KEYWORDS):
        reset_session(session_id)
        return (
            f"Oke, kita mulai dari awal ya 😊\n\n"
            f"Selamat datang di *{NAMA_TOKO}* 🏪\n"
            "Ada yang bisa saya bantu? Ketik *stok* untuk cek ketersediaan atau *pesan* untuk order LPG 3kg."
        )

    state = session.get("state", "greet")

    # ===== STATE: GREET =====
    if state == "greet":
        if any(k in msg_lower for k in GREETING_KEYWORDS):
            session["state"] = "main_menu"
            return (
                f"Halo! Selamat datang di *{NAMA_TOKO}* 🏪\n\n"
                "Saya Arza (AI) yang siap membantu kamu 24 jam 😊\n\n"
                "Mau ngapain nih?\n"
                "• Ketik *stok* — cek ketersediaan LPG\n"
                "• Ketik *pesan* — order LPG 3kg\n"
                "• Ketik *harga* — info harga"
            )
        else:
            session["state"] = "main_menu"
            # Langsung proses pesan pertama meski bukan greeting
            return handle_chat(message, session_id, no_wa)

    # ===== STATE: MAIN MENU =====
    if state == "main_menu":

        # --- CEK STOK ---
        if any(k in msg_lower for k in STOK_KEYWORDS):
            info = get_stok_lpg()
            if not info["tersedia"]:
                return (
                    "😔 Maaf kak, stok LPG 3kg sedang *kosong* saat ini.\n\n"
                    "Saya catat nomor kamu ya, nanti kami kabari kalau sudah restock 🙏"
                )
            status = "⚠️ Hampir habis" if info["hampir_habis"] else "✅ Tersedia"
            return (
                f"Info stok LPG 3kg {NAMA_TOKO}:\n\n"
                f"• Status: {status}\n"
                f"• Harga: Rp{info['harga']:,}/tabung\n\n"
                "Mau langsung pesan? Ketik *pesan* ya 😊"
            )

        # --- INFO HARGA ---
        if "harga" in msg_lower or "berapa" in msg_lower:
            info = get_stok_lpg()
            return (
                f"Harga LPG 3kg di {NAMA_TOKO}:\n\n"
                f"💰 *Rp{info['harga']:,}* per tabung\n\n"
                "Mau pesan? Ketik *pesan* ya 😊"
            )

        # --- MULAI ORDER ---
        if any(k in msg_lower for k in ORDER_KEYWORDS):
            # Cek stok dulu sebelum terima order
            info = get_stok_lpg()
            if not info["tersedia"]:
                return (
                    "😔 Maaf kak, stok LPG 3kg sedang *kosong*.\n"
                    "Kami akan kabari kamu saat sudah restock ya 🙏"
                )
            session["state"] = "ask_nama"
            return (
                "Siap, kita proses ordernya ya 😊\n\n"
                "Boleh kenalan dulu, *nama kamu siapa*? 🙏"
            )

        # Belum match keyword apapun
        return (
            f"Halo! Ada yang bisa saya bantu di *{NAMA_TOKO}*? 😊\n\n"
            "• Ketik *stok* — cek ketersediaan\n"
            "• Ketik *pesan* — order LPG 3kg\n"
            "• Ketik *harga* — info harga"
        )

    # ===== STATE: ASK NAMA =====
    if state == "ask_nama":
        nama = parse_nama(msg) or msg.strip().title()
        if len(nama) < 2:
            return "Boleh tahu nama kamu siapa ya? 😊"

        session["nama"] = nama
        session["state"] = "ask_jumlah"
        info = get_stok_lpg()
        return (
            f"Halo *{nama}* 😊\n\n"
            f"Mau pesan berapa tabung LPG 3kg?\n"
            f"_(Harga: Rp{info['harga']:,}/tabung)_"
        )

    # ===== STATE: ASK JUMLAH =====
    if state == "ask_jumlah":
        jumlah = parse_jumlah(msg)
        if not jumlah:
            return "Berapa tabung yang mau dipesan? Contoh: *2* atau *tiga* tabung 😊"

        info = get_stok_lpg()
        if jumlah > info["stok"]:
            return (
                f"Maaf kak, stok yang tersedia hanya *{info['stok']} tabung*.\n"
                f"Mau pesan berapa tabung? (maks {info['stok']})"
            )

        session["jumlah"] = jumlah
        session["state"] = "ask_metode"
        total = info["harga"] * jumlah
        return (
            f"Oke, *{jumlah} tabung* ya 👍\n"
            f"Total: *Rp{total:,}*\n\n"
            "Mau *ambil sendiri* ke toko atau *diantar*? 🏪🛵"
        )

    # ===== STATE: ASK METODE =====
    if state == "ask_metode":
        if any(k in msg_lower for k in METODE_ANTAR):
            session["metode"] = "Diantar"
            session["state"] = "ask_catatan"
            return (
                "Siap, diantar ya 🛵\n\n"
                "Boleh info *alamat lengkap* kamu? "
                "(atau ketik *skip* kalau mau isi nanti)"
            )
        elif any(k in msg_lower for k in METODE_AMBIL):
            session["metode"] = "Ambil Sendiri"
            session["state"] = "konfirmasi_order"
            return handle_chat("konfirmasi", session_id, no_wa)
        else:
            return (
                "Mau *ambil sendiri* ke toko atau *diantar* ke rumah? 😊\n"
                "_(Ketik salah satu)_"
            )

    # ===== STATE: ASK CATATAN (alamat untuk antar) =====
    if state == "ask_catatan":
        if "skip" in msg_lower:
            session["catatan"] = "Alamat belum diisi"
        else:
            session["catatan"] = msg.strip()
        session["state"] = "konfirmasi_order"
        return handle_chat("konfirmasi", session_id, no_wa)

    # ===== STATE: KONFIRMASI ORDER =====
    if state == "konfirmasi_order":
        info = get_stok_lpg()
        nama = session.get("nama", "-")
        jumlah = session.get("jumlah", 0)
        metode = session.get("metode", "Ambil Sendiri")
        catatan = session.get("catatan", "-")
        total = info["harga"] * jumlah

        detail_catatan = (
            f"\n• Alamat: {catatan}"
            if metode == "Diantar" and catatan and catatan != "-"
            else ""
        )

        return (
            f"📋 *Ringkasan Order*\n\n"
            f"• Nama: {nama}\n"
            f"• Produk: LPG 3kg\n"
            f"• Jumlah: {jumlah} tabung\n"
            f"• Harga: Rp{info['harga']:,}/tabung\n"
            f"• Total: *Rp{total:,}*\n"
            f"• Metode: {metode}"
            f"{detail_catatan}\n\n"
            "Ketik *konfirmasi* untuk lanjut, atau *batal* untuk cancel 🙏"
        )

    # ===== STATE: WAITING KONFIRMASI =====
    if state == "konfirmasi_order":
        if any(k in msg_lower for k in BATAL_KEYWORDS):
            reset_session(session_id)
            return "Order dibatalkan ya 🙏 Ketik *pesan* kalau mau order lagi 😊"

    # Handle konfirmasi dari state apapun yang menunggu jawaban iya/tidak
    if any(k in msg_lower for k in KONFIRMASI_KEYWORDS) and session.get("jumlah"):
        if session.get("state") in ["konfirmasi_order", "waiting_konfirmasi"]:
            # Proses order
            nama = session.get("nama", "Pelanggan")
            no_wa_pelanggan = session.get("no_wa") or session_id
            jumlah = session.get("jumlah", 1)
            metode = session.get("metode", "Ambil Sendiri")
            catatan = session.get("catatan", "Tidak ada catatan")

            result = catat_order(
                nama=nama,
                no_wa=no_wa_pelanggan,
                jumlah=jumlah,
                metode_ambil=metode,
                catatan=catatan,
                sumber="WA Bot",
            )

            session["state"] = "order_selesai"
            session["order_result"] = result

            if result["success"]:
                info = get_stok_lpg()
                pesan_bayar = (
                    "Pembayaran dilakukan saat *ambil di toko* ya 😊"
                    if metode == "Ambil Sendiri"
                    else "Pembayaran dilakukan saat *barang diantar* ya 😊"
                )
                return (
                    f"✅ *Order berhasil dicatat!*\n\n"
                    f"• ID Order: `{result['order_id']}`\n"
                    f"• Total: *Rp{result['total']:,}*\n"
                    f"• Metode: {metode}\n\n"
                    f"{pesan_bayar}\n\n"
                    f"Terima kasih sudah belanja di *{NAMA_TOKO}* 🙏😊\n"
                    "Ketik *pesan* lagi kalau butuh ya!"
                )
            else:
                return (
                    f"Order kamu sudah kami terima ya *{nama}* 😊\n\n"
                    f"• Total: *Rp{result['total']:,}*\n"
                    f"• Metode: {metode}\n\n"
                    f"Terima kasih sudah belanja di *{NAMA_TOKO}* 🙏"
                )

    if any(k in msg_lower for k in BATAL_KEYWORDS):
        reset_session(session_id)
        return "Order dibatalkan ya 🙏 Ketik *pesan* kapan saja kalau mau order lagi 😊"

    # ===== STATE: ORDER SELESAI =====
    if state == "order_selesai":
        # Pelanggan masih chat setelah order selesai
        if any(k in msg_lower for k in ORDER_KEYWORDS):
            reset_session(session_id)
            return handle_chat(message, session_id, no_wa)
        return (
            f"Ada yang bisa saya bantu lagi? 😊\n"
            "Ketik *pesan* untuk order baru atau *stok* untuk cek ketersediaan."
        )

    # ===== FALLBACK =====
    return get_ai_fallback(message, session)
