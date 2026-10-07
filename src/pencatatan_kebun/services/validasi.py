from datetime import date

from pencatatan_kebun.services.exception import TanggalTidakValidException


def cek_tanggal(teks, kolom: str = "tanggal_panen", boleh_masa_depan: bool = True) -> date:
    """Pastikan teks berupa tanggal YYYY-MM-DD yang ada di kalender.

    Formatnya ketat: "2026-1-5" dan "20261007" ditolak walaupun bisa dibaca
    date.fromisoformat, agar sama dengan isi database.

    Args:
        teks: Tanggal yang dicek.
        kolom: Isian form yang dicek, untuk disorot ui, mis. "tanggal_mulai".
        boleh_masa_depan: False untuk menolak tanggal setelah hari ini.

    Returns:
        Tanggal sebagai objek date.

    Raises:
        TanggalTidakValidException: Format salah, tanggal tidak ada di kalender
            (mis. 2026-02-30), atau di masa depan padahal tidak boleh.
    """
    try:
        tanggal = date.fromisoformat(teks)
    except (ValueError, TypeError):
        raise TanggalTidakValidException("Format harus YYYY-MM-DD", kolom=kolom)
    if tanggal.isoformat() != teks:
        raise TanggalTidakValidException("Format harus YYYY-MM-DD", kolom=kolom)
    if not boleh_masa_depan and tanggal > date.today():
        raise TanggalTidakValidException("Tidak boleh di masa depan", kolom=kolom)
    return tanggal
