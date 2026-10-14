"""Versi skema dan migrasi database.

Versi skema disimpan di dalam file database (PRAGMA user_version). Saat
koneksi dibuka:

- Database baru (kosong): dibuat dari skema.sql, versinya VERSI_SKEMA.
- Database lama: migrasi yang belum dijalankan dipakai satu per satu
  (MIGRASI[versi_lama + 1], ..., MIGRASI[VERSI_SKEMA]).
- Database dengan versi lebih tinggi dari VERSI_SKEMA (dibuat aplikasi yang
  lebih baru): ditolak, supaya aplikasi lama tidak merusaknya.

Database yang dibuat sebelum versi dicatat (user_version 0, tetapi tabelnya
sudah ada) dianggap versi 1.

Cara mengubah skema setelah aplikasi dipakai dengan data asli:

1. Ubah skema.sql: selalu skema lengkap terbaru, dipakai untuk database baru.
2. Naikkan VERSI_SKEMA.
3. Tambahkan fungsi di MIGRASI[VERSI_SKEMA] yang mengubah database versi
   sebelumnya menjadi sama dengan skema.sql yang baru, mis.
   conn.execute("ALTER TABLE pohon ADD COLUMN catatan TEXT"). Untuk perubahan
   yang tidak bisa dengan ALTER TABLE (mengubah CHECK, tipe kolom), buat tabel
   baru, salin datanya, hapus tabel lama, lalu ganti namanya
   (https://www.sqlite.org/lang_altertable.html#otheralter).
4. Jalankan tes: tests/test_migrasi.py membandingkan database versi 1
   (tests/acuan/skema_v1.sql) yang dimigrasi dengan database baru dari skema.sql.

Fungsi migrasi tidak boleh memakai executescript (langsung commit, sehingga
migrasi tidak bisa dibatalkan) dan tidak perlu commit sendiri.
"""
import sqlite3
from collections.abc import Callable

VERSI_SKEMA = 1

# versi tujuan -> fungsi yang mengubah database dari versi sebelumnya.
MIGRASI: dict[int, Callable[[sqlite3.Connection], None]] = {}


class VersiDatabaseTerlaluBaruError(Exception):
    """Database dibuat oleh versi aplikasi yang lebih baru."""

    def __init__(self, versi: int):
        self.versi = versi
        super().__init__(f"Data ini dibuat oleh versi aplikasi yang lebih baru (versi data "
                         f"{versi}, aplikasi ini sampai versi {VERSI_SKEMA}). Pakai versi "
                         "aplikasi terbaru. Data tidak diubah.")


class MigrasiGagalError(Exception):
    """Migrasi ke satu versi gagal; perubahan versi itu dibatalkan."""

    def __init__(self, versi: int):
        self.versi = versi
        super().__init__(f"Data tidak bisa diperbarui ke versi {versi}. Data tidak diubah.")


def versi_database(conn: sqlite3.Connection) -> int:
    """Versi skema yang tercatat di database (0 jika belum pernah dicatat)."""
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _ada_tabel(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table'").fetchone() is not None


def _catat_versi(conn: sqlite3.Connection, versi: int) -> None:
    conn.execute(f"PRAGMA user_version = {int(versi)}")


def _jalankan_migrasi(conn: sqlite3.Connection, versi: int) -> None:
    """Jalankan MIGRASI[versi] dalam satu transaksi.

    Foreign key dimatikan selama migrasi (wajib saat tabel dibuat ulang), lalu
    seluruh data dicek dengan foreign_key_check sebelum commit.

    Raises:
        MigrasiGagalError: Migrasi error atau meninggalkan data yang melanggar
            foreign key; semua perubahan versi itu dibatalkan.
    """
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        try:
            MIGRASI[versi](conn)
            if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise MigrasiGagalError(versi)
            _catat_versi(conn, versi)
            conn.commit()
        except Exception as e:
            conn.rollback()
            if isinstance(e, MigrasiGagalError):
                raise
            raise MigrasiGagalError(versi) from e
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def siapkan_skema(conn: sqlite3.Connection, skema_sql: str,
                  sebelum_migrasi: Callable[[int], None] | None = None) -> None:
    """Buat skema untuk database baru, atau migrasikan database lama ke VERSI_SKEMA.

    Args:
        conn: Koneksi database.
        skema_sql: Isi skema.sql (skema lengkap terbaru).
        sebelum_migrasi: Dipanggil dengan versi lama sebelum migrasi pertama
            dijalankan, mis. untuk mencadangkan data. Jika error, migrasi tidak
            dijalankan.

    Raises:
        VersiDatabaseTerlaluBaruError: Versi database di atas VERSI_SKEMA.
        MigrasiGagalError: Salah satu migrasi gagal. Migrasi yang sudah berhasil
            sebelumnya tetap tersimpan, dan versi database menunjukkan sampai
            mana migrasi berhasil.
    """
    versi = versi_database(conn)
    if versi == 0:
        if not _ada_tabel(conn):
            conn.executescript(skema_sql)
            _catat_versi(conn, VERSI_SKEMA)
            conn.commit()
            return
        versi = 1
        _catat_versi(conn, versi)
        conn.commit()
    if versi > VERSI_SKEMA:
        raise VersiDatabaseTerlaluBaruError(versi)
    if versi == VERSI_SKEMA:
        return
    if sebelum_migrasi is not None:
        sebelum_migrasi(versi)
    for tujuan in range(versi + 1, VERSI_SKEMA + 1):
        _jalankan_migrasi(conn, tujuan)
