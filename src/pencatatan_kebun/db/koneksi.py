import sqlite3
from datetime import datetime
from functools import partial
from pathlib import Path

from pencatatan_kebun.db.migrasi import MigrasiGagalError, siapkan_skema

SKEMA = Path(__file__).parent / "skema.sql"


def _cadangkan_sebelum_migrasi(conn: sqlite3.Connection, folder: Path, versi: int) -> None:
    """Salin database ke folder cadangan sebelum dimigrasi dari `versi`.

    Nama berawalan "sebelum-migrasi-" sehingga tidak ikut terhapus oleh
    pembatasan jumlah cadangan otomatis.

    Raises:
        MigrasiGagalError: Cadangan tidak bisa dibuat; migrasi tidak dijalankan.
    """
    lokasi = folder / f"sebelum-migrasi-v{versi}-{datetime.now():%Y%m%d-%H%M%S}.db"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        salinan = sqlite3.connect(lokasi)
        try:
            conn.backup(salinan)
        finally:
            salinan.close()
    except (OSError, sqlite3.Error) as e:
        raise MigrasiGagalError(versi + 1) from e


def buka_koneksi(lokasi, folder_cadangan: Path | None = None) -> sqlite3.Connection:
    """Buka database di `lokasi`, aktifkan foreign key, dan siapkan skemanya.

    Database baru dibuat dari skema.sql; database lama dimigrasikan ke versi
    skema terbaru (lihat db/migrasi.py).

    Args:
        lokasi: Path file database (foldernya dibuat jika belum ada), atau
            ":memory:" untuk tes (database baru yang kosong setiap kali).
        folder_cadangan: Jika diisi, database disalin ke folder ini sebelum
            dimigrasi, supaya data lama tetap ada jika migrasi keliru.

    Returns:
        Koneksi dengan row_factory = sqlite3.Row, jadi kolom hasil query bisa
        diakses dengan nama, mis. baris["nomor_pohon"].

    Raises:
        VersiDatabaseTerlaluBaruError: Database dibuat aplikasi versi lebih baru.
        MigrasiGagalError: Migrasi atau cadangan sebelum migrasi gagal.
    """
    if lokasi != ":memory:":
        lokasi = Path(lokasi)
        lokasi.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(lokasi)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    sebelum = None
    if folder_cadangan is not None:
        sebelum = partial(_cadangkan_sebelum_migrasi, conn, Path(folder_cadangan))
    try:
        siapkan_skema(conn, SKEMA.read_text(encoding="utf-8"), sebelum)
    except BaseException:
        conn.close()
        raise
    return conn
