import sqlite3
from pathlib import Path

SKEMA = Path(__file__).parent / "skema.sql"


def buka_koneksi(lokasi) -> sqlite3.Connection:
    """Buka database di `lokasi`, aktifkan foreign key, dan pastikan tabel ada.

    Parameter:
        lokasi: path file database (foldernya dibuat jika belum ada), atau
            ":memory:" untuk tes (database baru yang kosong setiap kali).

    Mengembalikan: koneksi dengan row_factory = sqlite3.Row, jadi kolom hasil
        query bisa diakses dengan nama, mis. baris["nomor_pohon"].

    skema.sql dijalankan setiap kali koneksi dibuka. Karena memakai
    CREATE ... IF NOT EXISTS, tabel yang sudah ada tidak ikut diperbarui: setelah
    skema diubah, file database lama perlu dihapus (atau dimigrasi jika sudah
    berisi data asli).
    """
    if lokasi != ":memory:":
        lokasi = Path(lokasi)
        lokasi.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(lokasi)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SKEMA.read_text(encoding="utf-8"))
    return conn
