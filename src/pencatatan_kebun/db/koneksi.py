import sqlite3
from pathlib import Path

SKEMA = Path(__file__).parent / "skema.sql"


def buka_koneksi(lokasi) -> sqlite3.Connection:
    """Buka database di `lokasi`, aktifkan foreign key, dan pastikan tabel ada.

    `lokasi` bisa path file, atau ":memory:" untuk tes.
    """
    if lokasi != ":memory:":
        lokasi = Path(lokasi)
        lokasi.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(lokasi)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SKEMA.read_text(encoding="utf-8"))
    return conn
