import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pencatatan_kebun.db import migrasi
from pencatatan_kebun.db.koneksi import SKEMA, buka_koneksi
from pencatatan_kebun.db.migrasi import (
    MigrasiGagalError,
    VersiDatabaseTerlaluBaruError,
    siapkan_skema,
    versi_database,
)

SKEMA_V1 = Path(__file__).parent / "acuan" / "skema_v1.sql"


def buat_db_v1(lokasi, versi=1) -> None:
    """Database dengan skema versi 1 dan satu jenis tanaman."""
    conn = sqlite3.connect(lokasi)
    conn.executescript(SKEMA_V1.read_text(encoding="utf-8"))
    conn.execute("INSERT INTO jenis_tanaman VALUES ('j1', 'Durian', NULL)")
    conn.execute(f"PRAGMA user_version = {versi}")
    conn.commit()
    conn.close()


def struktur(conn: sqlite3.Connection) -> dict:
    """Struktur database untuk dibandingkan: kolom (urut), foreign key,
    index, dan trigger. CHECK tidak ikut dibandingkan (hanya ada di teks
    CREATE TABLE, yang berbeda setelah ALTER TABLE)."""
    hasil = {}
    tabel = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name")]
    for nama in tabel:
        index = []
        for r in conn.execute(f"PRAGMA index_list({nama})"):
            kolom = tuple(k[2] for k in conn.execute(f"PRAGMA index_info({r[1]})"))
            # Nama sqlite_autoindex_* bergantung pada urutan constraint, jadi tidak dipakai.
            index.append((None if r[1].startswith("sqlite_autoindex") else r[1], r[2], r[3], kolom))
        hasil[nama] = {
            "kolom": [tuple(r[1:]) for r in conn.execute(f"PRAGMA table_info({nama})")],
            "fk": sorted(tuple(r[2:]) for r in conn.execute(f"PRAGMA foreign_key_list({nama})")),
            "index": sorted(index, key=repr),
        }
    hasil["trigger"] = {r[0]: re.sub(r"\s+", " ", r[1]).strip() for r in conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='trigger'")}
    return hasil


class DasarMigrasi(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder, True)
        self.lokasi = self.folder / "kebun.db"

    def buka(self, **kw):
        conn = buka_koneksi(self.lokasi, **kw)
        self.addCleanup(conn.close)
        return conn

    def kolom(self, conn, tabel):
        return [r[1] for r in conn.execute(f"PRAGMA table_info({tabel})")]


class TestVersi(DasarMigrasi):
    def test_database_baru_memakai_versi_terbaru(self):
        conn = self.buka()
        self.assertEqual(versi_database(conn), migrasi.VERSI_SKEMA)
        self.assertIn("jenis_tanaman", {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")})

    def test_database_tanpa_versi_dianggap_versi_1(self):
        # Database yang dibuat sebelum versi skema dicatat.
        buat_db_v1(self.lokasi, versi=0)
        conn = self.buka()
        self.assertEqual(versi_database(conn), 1)
        self.assertEqual(conn.execute("SELECT nama_jenis FROM jenis_tanaman").fetchone()[0],
                         "Durian")

    def test_database_versi_lebih_baru_ditolak(self):
        buat_db_v1(self.lokasi, versi=migrasi.VERSI_SKEMA + 1)
        with self.assertRaises(VersiDatabaseTerlaluBaruError):
            buka_koneksi(self.lokasi)
        # Koneksi sudah ditutup: file bisa dihapus (Windows mengunci file yang terbuka).
        self.lokasi.unlink()

    def test_versi_terbaru_tanpa_migrasi_tidak_membuat_cadangan(self):
        self.buka(folder_cadangan=self.folder / "cadangan").close()
        self.buka(folder_cadangan=self.folder / "cadangan")
        self.assertFalse((self.folder / "cadangan").exists())


class TestSkemaV1(DasarMigrasi):
    def test_database_v1_dimigrasi_sama_dengan_skema_terbaru(self):
        """Gagal jika skema.sql diubah tanpa menaikkan VERSI_SKEMA dan menambah
        migrasi yang sesuai (lihat db/migrasi.py)."""
        buat_db_v1(self.lokasi)
        lama = self.buka()
        baru = buka_koneksi(":memory:")
        self.addCleanup(baru.close)
        self.assertEqual(struktur(lama), struktur(baru))
        self.assertEqual(versi_database(lama), versi_database(baru))


def tambah_kolom(conn):
    conn.execute("ALTER TABLE jenis_tanaman ADD COLUMN warna TEXT")


class TestMenjalankanMigrasi(DasarMigrasi):
    """Memakai migrasi tiruan ke versi 2."""

    def setUp(self):
        super().setUp()
        buat_db_v1(self.lokasi)
        self.enterContext(mock.patch.object(migrasi, "VERSI_SKEMA", 2))

    def migrasi_ke_2(self, fungsi):
        self.enterContext(mock.patch.dict(migrasi.MIGRASI, {2: fungsi}))

    def test_migrasi_dijalankan_dan_versi_dicatat(self):
        self.migrasi_ke_2(tambah_kolom)
        conn = self.buka()
        self.assertEqual(versi_database(conn), 2)
        self.assertIn("warna", self.kolom(conn, "jenis_tanaman"))
        self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_migrasi_error_dibatalkan_semua(self):
        def gagal(conn):
            tambah_kolom(conn)
            raise ValueError("salah tulis migrasi")
        self.migrasi_ke_2(gagal)
        with self.assertRaises(MigrasiGagalError) as e:
            buka_koneksi(self.lokasi)
        self.assertEqual(e.exception.versi, 2)
        conn = sqlite3.connect(self.lokasi)
        self.addCleanup(conn.close)
        self.assertEqual(versi_database(conn), 1)
        self.assertNotIn("warna", self.kolom(conn, "jenis_tanaman"))

    def test_migrasi_yang_merusak_foreign_key_dibatalkan(self):
        def rusak(conn):
            conn.execute("INSERT INTO varietas VALUES ('v1', 'tidak-ada', 'Bawor', NULL)")
        self.migrasi_ke_2(rusak)
        with self.assertRaises(MigrasiGagalError):
            buka_koneksi(self.lokasi)
        conn = sqlite3.connect(self.lokasi)
        self.addCleanup(conn.close)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM varietas").fetchone()[0], 0)

    def test_cadangan_dibuat_sebelum_migrasi(self):
        self.migrasi_ke_2(tambah_kolom)
        self.buka(folder_cadangan=self.folder / "cadangan")
        [cadangan] = (self.folder / "cadangan").glob("sebelum-migrasi-v1-*.db")
        salinan = sqlite3.connect(cadangan)
        self.addCleanup(salinan.close)
        self.assertEqual(versi_database(salinan), 1)
        self.assertNotIn("warna", self.kolom(salinan, "jenis_tanaman"))

    def test_cadangan_gagal_migrasi_tidak_dijalankan(self):
        self.migrasi_ke_2(tambah_kolom)
        tidak_bisa = self.folder / "file-biasa"
        tidak_bisa.write_text("bukan folder", encoding="utf-8")
        with self.assertRaises(MigrasiGagalError):
            buka_koneksi(self.lokasi, folder_cadangan=tidak_bisa)
        conn = sqlite3.connect(self.lokasi)
        self.addCleanup(conn.close)
        self.assertEqual(versi_database(conn), 1)

    def test_database_baru_langsung_versi_terbaru_tanpa_migrasi(self):
        dipanggil = mock.Mock()
        self.migrasi_ke_2(dipanggil)
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        siapkan_skema(conn, SKEMA.read_text(encoding="utf-8"))
        self.assertEqual(versi_database(conn), 2)
        dipanggil.assert_not_called()


if __name__ == "__main__":
    unittest.main()
