import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pencatatan_kebun.db.koneksi import buka_koneksi
from pencatatan_kebun.models import PeriodePanen, Pohon
from pencatatan_kebun.services.exception import (
    DataSudahAdaException,
    DataTidakDitemukanException,
    JumlahBuahTidakValidException,
    TanggalTidakValidException,
)
from pencatatan_kebun.services.master import MasterService
from pencatatan_kebun.services.panen import PanenService
from pencatatan_kebun.services.periode import PeriodeService
from pencatatan_kebun.services.stok import StokService


class DasarStok(unittest.TestCase):
    """Persiapan bersama; tidak berisi tes."""

    def setUp(self):
        self.conn = buka_koneksi(":memory:")
        self.addCleanup(self.conn.close)
        self.master = MasterService(self.conn)
        self.panen = PanenService(self.conn)
        self.service = StokService(self.conn)

        durian = self.master.tambah_jenis("Durian")
        self.bawor = self.master.tambah_varietas(durian, "Bawor")
        self.montong = self.master.tambah_varietas(durian, "Montong")
        self.pohon_7 = self.master.tambah_pohon(self.bawor, 7)
        self.pohon_2 = self.master.tambah_pohon(self.bawor, 2)
        self.montong_1 = self.master.tambah_pohon(self.montong, 1)
        self.baik = self.master.tambah_keterangan("Baik")
        self.gugur = self.master.tambah_keterangan("Gugur")
        self.periode = PeriodeService(self.conn).buka_periode("Raya 2025", "2025-01-01", "2025-03-31")

    def catat(self, **ubah):
        data = {"pohon": self.pohon_7, "periode": self.periode, "jumlah_buah": 11,
                    "tanggal_hitung": "2025-01-05"}
        data.update(ubah)
        return self.service.catat_stok(**data)

    def catat_buah(self, tanggal, pohon=None, keterangan=None):
        self.panen.catat_buah(pohon or self.pohon_7, keterangan or self.baik, 2.0, tanggal)

    def assertTersimpan(self):
        """Service harus commit sendiri: tidak ada transaksi yang tertinggal."""
        self.assertFalse(self.conn.in_transaction)


class TestCatatStok(DasarStok):
    def test_catat_tersimpan(self):
        self.catat()
        self.assertTersimpan()
        hasil = self.service.repo_stok.read(self.pohon_7.get_id_pohon(), self.periode.get_id_periode())
        self.assertEqual(hasil.get_jumlah_buah(), 11)
        self.assertEqual(hasil.get_tanggal_hitung(), "2025-01-05")
        self.assertEqual(hasil.get_pohon().get_varietas().get_nama_varietas(), "Bawor")
        self.assertEqual(hasil.get_periode().get_nama(), "Raya 2025")

    def test_jumlah_nol_boleh(self):
        self.catat(jumlah_buah=0)

    def test_jumlah_tidak_valid_ditolak(self):
        for jumlah in (-1, 1.5, "11", None, True):
            with self.subTest(jumlah=jumlah):
                with self.assertRaises(JumlahBuahTidakValidException) as cm:
                    self.catat(jumlah_buah=jumlah)
                self.assertEqual(cm.exception.kolom, "jumlah_buah")

    def test_tanggal_tidak_valid_ditolak(self):
        besok = (date.today() + timedelta(days=1)).isoformat()
        for tanggal in ("2025-02-30", "05-01-2025", "", None, besok):
            with self.subTest(tanggal=tanggal):
                with self.assertRaises(TanggalTidakValidException) as cm:
                    self.catat(tanggal_hitung=tanggal)
                self.assertEqual(cm.exception.kolom, "tanggal_hitung")

    def test_data_master_tidak_ada_di_database_ditolak(self):
        kasus = {
            "pohon": {"pohon": Pohon(99, self.bawor)},
            "periode_panen": {"periode": PeriodePanen("Lain", "2024-01-01", "2024-02-01")},
        }
        for kolom, ubah in kasus.items():
            with self.subTest(kolom=kolom):
                with self.assertRaises(DataTidakDitemukanException) as cm:
                    self.catat(**ubah)
                self.assertEqual(cm.exception.kolom, kolom)

    def test_stok_ganda_di_periode_sama_ditolak(self):
        self.catat()
        with self.assertRaises(DataSudahAdaException) as cm:
            self.catat(jumlah_buah=5)
        self.assertEqual(cm.exception.kolom, "pohon")
        self.assertIn("Bawor 7", cm.exception.pesan)

    def test_pohon_lain_atau_periode_lain_boleh(self):
        lama = PeriodeService(self.conn).buka_periode("Raya 2024", "2024-01-01", "2024-03-31")
        self.catat()
        self.catat(pohon=self.pohon_2)
        self.catat(periode=lama, tanggal_hitung="2024-01-05")
        self.assertEqual(len(self.service.daftar_stok_periode(self.periode.get_id_periode())), 2)

    def test_jumlah_kurang_dari_buah_tercatat_ditolak(self):
        self.catat_buah("2025-01-10")
        self.catat_buah("2025-01-11", keterangan=self.gugur)
        with self.assertRaises(JumlahBuahTidakValidException) as cm:
            self.catat(jumlah_buah=1)
        self.assertIn("2 buah", cm.exception.pesan)
        self.catat(jumlah_buah=2)


class TestUbahDanHapusStok(DasarStok):
    def test_ubah(self):
        self.catat()
        hasil = self.service.ubah_stok(self.pohon_7, self.periode, 20, "2025-01-06")
        self.assertTersimpan()
        self.assertEqual(hasil.get_jumlah_buah(), 20)
        self.assertEqual(hasil.get_tanggal_hitung(), "2025-01-06")

    def test_ubah_isian_tidak_valid_ditolak(self):
        self.catat()
        with self.assertRaises(JumlahBuahTidakValidException):
            self.service.ubah_stok(self.pohon_7, self.periode, -1, "2025-01-05")
        self.assertEqual(self.service.sisa_buah(
            self.pohon_7.get_id_pohon(), self.periode.get_id_periode()), 11)

    def test_ubah_ke_kurang_dari_buah_tercatat_ditolak(self):
        self.catat()
        for tanggal in ("2025-01-10", "2025-01-11", "2025-01-12"):
            self.catat_buah(tanggal)
        with self.assertRaises(JumlahBuahTidakValidException):
            self.service.ubah_stok(self.pohon_7, self.periode, 2, "2025-01-05")

    def test_ubah_stok_yang_belum_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException):
            self.service.ubah_stok(self.pohon_7, self.periode, 5, "2025-01-05")

    def test_hapus(self):
        self.catat()
        self.catat_buah("2025-01-10")
        self.service.hapus_stok(self.pohon_7.get_id_pohon(), self.periode.get_id_periode())
        self.assertTersimpan()
        self.assertIsNone(self.service.repo_stok.read(
            self.pohon_7.get_id_pohon(), self.periode.get_id_periode()))
        self.assertEqual(len(self.panen.repo_buah.read_all()), 1)

    def test_hapus_stok_yang_tidak_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException):
            self.service.hapus_stok(self.pohon_7.get_id_pohon(), self.periode.get_id_periode())


class TestSisaBuah(DasarStok):
    def test_sisa_dikurangi_buah_di_dalam_periode_termasuk_gugur(self):
        self.catat(jumlah_buah=11)
        self.catat_buah("2024-12-31")
        self.catat_buah("2025-01-01")
        self.catat_buah("2025-02-15", keterangan=self.gugur)
        self.catat_buah("2025-03-31")
        self.catat_buah("2025-04-01")
        self.catat_buah("2025-02-01", pohon=self.pohon_2)
        self.assertEqual(self.service.sisa_buah(
            self.pohon_7.get_id_pohon(), self.periode.get_id_periode()), 8)

    def test_sisa_periode_aktif_sampai_hari_ini(self):
        aktif = PeriodeService(self.conn).buka_periode("Berjalan", "2025-06-01")
        self.catat(periode=aktif, jumlah_buah=5, tanggal_hitung="2025-06-02")
        self.catat_buah("2025-06-10")
        self.catat_buah(date.today().isoformat())
        self.assertEqual(self.service.sisa_buah(
            self.pohon_7.get_id_pohon(), aktif.get_id_periode()), 3)

    def test_sisa_tanpa_stok_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException):
            self.service.sisa_buah(self.pohon_7.get_id_pohon(), self.periode.get_id_periode())

    def test_daftar_stok_periode(self):
        self.catat(pohon=self.pohon_7, jumlah_buah=11)
        self.catat(pohon=self.montong_1, jumlah_buah=13)
        self.catat(pohon=self.pohon_2, jumlah_buah=0)
        self.catat_buah("2025-01-10")
        self.catat_buah("2025-01-11", keterangan=self.gugur)
        self.catat_buah("2025-01-10", pohon=self.montong_1)

        hasil = self.service.daftar_stok_periode(self.periode.get_id_periode())
        self.assertEqual(
            [(d["stok"].get_pohon().get_varietas().get_nama_varietas(),
              d["stok"].get_pohon().get_nomor_pohon(),
              d["stok"].get_jumlah_buah(), d["jumlah_tercatat"], d["sisa"]) for d in hasil],
            [("Bawor", 2, 0, 0, 0), ("Bawor", 7, 11, 2, 9), ("Montong", 1, 13, 1, 12)])

    def test_daftar_stok_periode_kosong(self):
        self.assertEqual(self.service.daftar_stok_periode(self.periode.get_id_periode()), [])

    def test_daftar_stok_periode_tidak_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException) as cm:
            self.service.daftar_stok_periode("tidak-ada")
        self.assertEqual(cm.exception.kolom, "periode_panen")


if __name__ == "__main__":
    unittest.main()
