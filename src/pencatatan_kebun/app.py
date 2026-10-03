from pencatatan_kebun.config import lokasi_db
from pencatatan_kebun.db.koneksi import buka_koneksi


def jalankan(lokasi=None) -> None:
    conn = buka_koneksi(lokasi if lokasi is not None else lokasi_db())
    try:
        # Jendela utama (ui) akan dibuka di sini nanti.
        pass
    finally:
        conn.close()
