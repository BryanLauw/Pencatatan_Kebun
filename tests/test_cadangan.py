import shutil
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pencatatan_kebun.cadangan import (
    CadanganGagalException,
    CadanganService,
    CadanganTidakValidException,
    cadangan_otomatis,
    daftar_cadangan_otomatis,
    nama_file_bawaan,
    pulihkan_cadangan,
    simpan_cadangan,
)
from pencatatan_kebun.db.koneksi import buka_koneksi
from pencatatan_kebun.services.master import MasterService


class DasarCadangan(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder, True)
        self.conn = buka_koneksi(self.folder / "kebun.db")
        self.addCleanup(self.conn.close)
        self.master = MasterService(self.conn)
        self.master.tambah_jenis("Durian")

    def nama_jenis(self, conn=None):
        return [j.get_nama_jenis() for j in MasterService(conn or self.conn).daftar_jenis()]


class TestSimpan(DasarCadangan):
    def test_cadangan_berisi_data(self):
        tujuan = self.folder / "flashdisk" / "cadangan.db"
        simpan_cadangan(self.conn, tujuan)
        salinan = sqlite3.connect(tujuan)
        self.addCleanup(salinan.close)
        self.assertEqual(salinan.execute("SELECT nama_jenis FROM jenis_tanaman").fetchall(),
                         [("Durian",)])

    def test_tujuan_tidak_bisa_ditulis(self):
        # Folder dengan nama yang sama dengan file tujuan: tidak bisa ditulis.
        tujuan = self.folder / "folder.db"
        tujuan.mkdir()
        with self.assertRaises(CadanganGagalException):
            simpan_cadangan(self.conn, tujuan)

    def test_nama_file_bawaan(self):
        self.assertEqual(nama_file_bawaan(datetime(2026, 10, 14, 9, 5)),
                         "Cadangan Kebun 14-10-2026.db")


class TestOtomatis(DasarCadangan):
    def test_hanya_simpan_yang_terbaru(self):
        folder = self.folder / "cadangan"
        awal = datetime(2026, 10, 1, 8, 0)
        for i in range(5):
            cadangan_otomatis(self.conn, folder, simpan=3, waktu=awal + timedelta(hours=i))
        daftar = daftar_cadangan_otomatis(folder)
        self.assertEqual([f.name for f in daftar],
                         ["kebun-20261001-120000.db", "kebun-20261001-110000.db",
                          "kebun-20261001-100000.db"])


class TestPulihkan(DasarCadangan):
    def test_pulihkan_mengganti_semua_data(self):
        cadangan = self.folder / "cadangan.db"
        simpan_cadangan(self.conn, cadangan)
        self.master.tambah_jenis("Alpukat")
        pulihkan_cadangan(self.conn, cadangan)
        self.assertEqual(self.nama_jenis(), ["Durian"])

    def test_koneksi_tetap_memakai_foreign_key_setelah_pulihkan(self):
        cadangan = self.folder / "cadangan.db"
        simpan_cadangan(self.conn, cadangan)
        pulihkan_cadangan(self.conn, cadangan)
        self.assertEqual(self.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_file_tidak_valid_ditolak_dan_data_tidak_berubah(self):
        teks = self.folder / "bukan.db"
        teks.write_text("bukan database", encoding="utf-8")
        lain = self.folder / "lain.db"
        sqlite3.connect(lain).execute("CREATE TABLE apa (x)").connection.close()
        for sumber in (teks, lain, self.folder / "tidak_ada.db"):
            with self.subTest(sumber=sumber.name), self.assertRaises(CadanganTidakValidException):
                pulihkan_cadangan(self.conn, sumber)
        self.assertEqual(self.nama_jenis(), ["Durian"])


class TestService(DasarCadangan):
    def test_pulihkan_mencadangkan_data_sekarang_dulu(self):
        service = CadanganService(self.conn, self.folder / "cadangan")
        lama = self.folder / "lama.db"
        service.simpan(lama)
        self.master.tambah_jenis("Alpukat")

        sebelum = service.pulihkan(lama)
        self.assertEqual(self.nama_jenis(), ["Durian"])
        # Data sebelum dipulihkan (dengan Alpukat) masih ada di cadangan otomatis.
        conn = sqlite3.connect(sebelum)
        self.addCleanup(conn.close)
        self.assertEqual(sorted(r[0] for r in conn.execute("SELECT nama_jenis FROM jenis_tanaman")),
                         ["Alpukat", "Durian"])

    def test_file_tidak_valid_tidak_membuat_cadangan_otomatis(self):
        service = CadanganService(self.conn, self.folder / "cadangan")
        teks = self.folder / "bukan.db"
        teks.write_text("x", encoding="utf-8")
        with self.assertRaises(CadanganTidakValidException):
            service.pulihkan(teks)
        self.assertEqual(daftar_cadangan_otomatis(service.folder_otomatis), [])


if __name__ == "__main__":
    unittest.main()
