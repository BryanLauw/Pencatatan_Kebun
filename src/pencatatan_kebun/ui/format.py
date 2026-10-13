"""Konversi teks isian form <-> nilai untuk service, dan format angka untuk tampilan.

Fungsi di sini tidak memakai tkinter, jadi bisa diuji dengan unittest.
Jika teks tidak bisa diubah, fungsi konversi mengembalikan None, supaya service
yang melempar exception dengan pesan standar. Tanggal tidak diketik, tetapi
dipilih lewat kalender (lihat kalender.py).
"""
import math
import re
from datetime import datetime

from pencatatan_kebun.config import FORMAT_TANGGAL_TAMPIL

FORMAT_TANGGAL_DB = "%Y-%m-%d"

_POLA_INT = re.compile(r"[+-]?\d+")


def teks_ke_bobot(teks: str | None) -> float | None:
    """Ubah isian bobot menjadi float. Koma desimal diterima ("2,5" -> 2.5).

    Args:
        teks: Isian bobot dari form.

    Returns:
        Bobot dalam kg, atau None jika kosong atau bukan angka (termasuk
        "nan"/"inf").
    """
    teks = (teks or "").strip().replace(",", ".")
    if teks == "":
        return None
    try:
        nilai = float(teks)
    except ValueError:
        return None
    return nilai if math.isfinite(nilai) else None


def teks_ke_int(teks: str | None) -> int | None:
    """Ubah isian bilangan bulat (nomor pohon, jumlah buah) menjadi int.

    Args:
        teks: Isian dari form.

    Returns:
        Bilangan bulat, atau None jika kosong atau bukan bilangan bulat
        (mis. "7,5" atau "abc").
    """
    teks = (teks or "").strip()
    if not _POLA_INT.fullmatch(teks):
        return None
    return int(teks)


def tanggal_ke_tampil(teks_db: str | None) -> str:
    """Ubah tanggal YYYY-MM-DD dari model menjadi DD-MM-YYYY.

    Args:
        teks_db: Tanggal dari model, atau None.

    Returns:
        Teks DD-MM-YYYY; "" jika None; teks apa adanya jika formatnya salah.
    """
    if not teks_db:
        return ""
    try:
        return datetime.strptime(teks_db, FORMAT_TANGGAL_DB).strftime(FORMAT_TANGGAL_TAMPIL)
    except ValueError:
        return teks_db


def kalimat(teks: str) -> str:
    """Huruf pertama dijadikan kapital tanpa mengubah huruf lain.

    Berbeda dengan str.capitalize() yang mengecilkan sisanya
    ("periode Raya 2026" tetap "Periode Raya 2026", bukan "Periode raya 2026").
    """
    return teks[:1].upper() + teks[1:]


def _angka_indonesia(nilai: float, desimal: int) -> str:
    """Format angka dengan titik ribuan dan koma desimal, mis. 1.234,50."""
    teks = f"{nilai:,.{desimal}f}"
    return teks.replace(",", "_").replace(".", ",").replace("_", ".")


def format_kg(nilai: float | None, desimal: int = 2) -> str:
    """Format bobot untuk tampilan, mis. 2.5 -> "2,50".

    Args:
        nilai: Bobot dalam kg, atau None.
        desimal: Jumlah angka di belakang koma.

    Returns:
        Teks angka; "-" jika None.
    """
    if nilai is None:
        return "-"
    return _angka_indonesia(nilai, desimal)


def format_persen(nilai: float | None) -> str:
    """Format persentase (0-100) dengan 1 desimal, mis. 12.345 -> "12,3%".

    Args:
        nilai: Persentase 0-100 (seperti dari LaporanService), atau None.

    Returns:
        Teks persen; "-" jika None.
    """
    if nilai is None:
        return "-"
    return _angka_indonesia(nilai, 1) + "%"
