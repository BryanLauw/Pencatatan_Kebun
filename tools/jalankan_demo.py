"""Jalankan aplikasi dengan database demo (berisi data contoh) untuk mengembangkan UI.

Dari folder proyek:

    .venv\\Scripts\\python tools\\jalankan_demo.py            # pakai data/demo/kebun.db
    .venv\\Scripts\\python tools\\jalankan_demo.py --reset    # isi ulang dari nol

Database demo ada di data/demo/ (diabaikan git) dan terpisah dari database asli di
%APPDATA%\\PencatatanKebun. Data contoh sama dengan yang dipakai untuk gambar panduan.
Perubahan yang dibuat saat mencoba aplikasi tersimpan sampai dijalankan dengan --reset.
"""
import shutil
import sys
from pathlib import Path

PROYEK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROYEK / "src"))
sys.path.insert(0, str(PROYEK / "docs" / "panduan"))

from ambil_gambar import isi_contoh  # noqa: E402
from pencatatan_kebun.app import jalankan  # noqa: E402
from pencatatan_kebun.db.koneksi import buka_koneksi  # noqa: E402

FOLDER_DEMO = PROYEK / "data" / "demo"
LOKASI_DEMO = FOLDER_DEMO / "kebun.db"


def main() -> None:
    if "--reset" in sys.argv:
        shutil.rmtree(FOLDER_DEMO, ignore_errors=True)
    if not LOKASI_DEMO.exists():
        FOLDER_DEMO.mkdir(parents=True, exist_ok=True)
        conn = buka_koneksi(LOKASI_DEMO)
        isi_contoh(conn)
        conn.close()
        print("Database demo dibuat:", LOKASI_DEMO)
    jalankan(LOKASI_DEMO)


if __name__ == "__main__":
    main()
