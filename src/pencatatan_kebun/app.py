from pencatatan_kebun.config import lokasi_db
from pencatatan_kebun.db.koneksi import buka_koneksi


def jalankan(lokasi=None) -> None:
    """Jalankan aplikasi: buka database, tampilkan ui, lalu tutup koneksi.

    Koneksi selalu ditutup saat aplikasi selesai, termasuk jika terjadi error.

    Args:
        lokasi: Path database. Jika None, dipakai lokasi_db() di folder data
            pengguna. Diisi lain (mis. folder sementara) untuk tes.
    """
    conn = buka_koneksi(lokasi if lokasi is not None else lokasi_db())
    try:
        # Jendela utama (ui) akan dibuka di sini nanti.
        pass
    finally:
        conn.close()
