import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pencatatan_kebun.db.koneksi import buka_koneksi
from pencatatan_kebun.models import KeteranganBuah, PeriodePanen, Pohon, Varietas
from pencatatan_kebun.repo.periode_panen import RepoPeriodePanen
from pencatatan_kebun.services.exception import (
    BobotTidakValidException,
    DataTidakDitemukanException,
    TanggalTidakValidException,
)
from pencatatan_kebun.services.master import MasterService
from pencatatan_kebun.services.panen import PanenService


class DasarPanen(unittest.TestCase):
    """Persiapan bersama; tidak berisi tes."""

    def setUp(self):
        self.conn = buka_koneksi(":memory:")
        self.addCleanup(self.conn.close)
        self.master = MasterService(self.conn)
        self.service = PanenService(self.conn)

        self.durian = self.master.tambah_jenis("Durian")
        self.musang_king = self.master.tambah_varietas(self.durian, "Musang King")
        self.pohon_7 = self.master.tambah_pohon(7)
        self.pohon_2 = self.master.tambah_pohon(2)
        self.baik = self.master.tambah_keterangan("Baik")

    def catat(self, **ubah):
        data = dict(pohon=self.pohon_7, varietas=self.musang_king, keterangan_buah=self.baik,
                    bobot=1.25, tanggal_panen="2025-01-15")
        data.update(ubah)
        return self.service.catat_buah(**data)

    def assertTersimpan(self):
        """Service harus commit sendiri: tidak ada transaksi yang tertinggal."""
        self.assertFalse(self.conn.in_transaction)


class TestCatatBuah(DasarPanen):
    def test_catat_tersimpan(self):
        buah = self.catat()
        self.assertTersimpan()
        hasil = self.service.repo_buah.read(buah.get_id_buah())
        self.assertEqual(hasil.get_pohon().get_nomor_pohon(), 7)
        self.assertEqual(hasil.get_varietas().get_nama_varietas(), "Musang King")
        self.assertEqual(hasil.get_varietas().get_jenis().get_nama_jenis(), "Durian")
        self.assertEqual(hasil.get_keterangan().get_nama_keterangan(), "Baik")
        self.assertEqual(hasil.get_bobot(), 1.25)
        self.assertEqual(hasil.get_tanggal_panen(), "2025-01-15")

    def test_bobot_bilangan_bulat_boleh(self):
        self.catat(bobot=2)

    def test_bobot_tidak_valid_ditolak(self):
        for bobot in (0, -1.5, "1.5", None, True):
            with self.subTest(bobot=bobot):
                with self.assertRaises(BobotTidakValidException) as cm:
                    self.catat(bobot=bobot)
                self.assertEqual(cm.exception.kolom, "bobot")

    def test_tanggal_hari_ini_boleh(self):
        self.catat(tanggal_panen=date.today().isoformat())

    def test_tanggal_tidak_valid_ditolak(self):
        for tanggal in ("2025-02-30", "15-01-2025", "2025-1-5", "20250115", "", None):
            with self.subTest(tanggal=tanggal):
                with self.assertRaises(TanggalTidakValidException) as cm:
                    self.catat(tanggal_panen=tanggal)
                self.assertEqual(cm.exception.kolom, "tanggal_panen")

    def test_tanggal_masa_depan_ditolak(self):
        besok = (date.today() + timedelta(days=1)).isoformat()
        with self.assertRaises(TanggalTidakValidException):
            self.catat(tanggal_panen=besok)

    def test_data_master_tidak_ada_di_database_ditolak(self):
        kasus = {
            "pohon": dict(pohon=Pohon(99)),
            "varietas": dict(varietas=Varietas("Bawor", self.durian)),
            "keterangan_buah": dict(keterangan_buah=KeteranganBuah("Busuk")),
        }
        for kolom, ubah in kasus.items():
            with self.subTest(kolom=kolom):
                with self.assertRaises(DataTidakDitemukanException) as cm:
                    self.catat(**ubah)
                self.assertEqual(cm.exception.kolom, kolom)
        self.assertEqual(self.service.repo_buah.read_all(), [])


class TestUbahDanHapusBuah(DasarPanen):
    def test_ubah(self):
        buah = self.catat()
        busuk = self.master.tambah_keterangan("Busuk")
        self.service.ubah_catatan_buah(buah.get_id_buah(), self.pohon_2, self.musang_king,
                                       busuk, 2.5, "2025-01-16")
        self.assertTersimpan()
        hasil = self.service.repo_buah.read(buah.get_id_buah())
        self.assertEqual(hasil.get_pohon().get_nomor_pohon(), 2)
        self.assertEqual(hasil.get_keterangan().get_nama_keterangan(), "Busuk")
        self.assertEqual(hasil.get_bobot(), 2.5)
        self.assertEqual(hasil.get_tanggal_panen(), "2025-01-16")

    def test_ubah_isian_tidak_valid_ditolak(self):
        buah = self.catat()
        with self.assertRaises(BobotTidakValidException):
            self.service.ubah_catatan_buah(buah.get_id_buah(), self.pohon_7, self.musang_king,
                                           self.baik, 0, "2025-01-15")
        self.assertEqual(self.service.repo_buah.read(buah.get_id_buah()).get_bobot(), 1.25)

    def test_ubah_id_tidak_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException):
            self.service.ubah_catatan_buah("tidak-ada", self.pohon_7, self.musang_king,
                                           self.baik, 1.0, "2025-01-15")

    def test_hapus(self):
        buah = self.catat()
        self.service.hapus_catatan_buah(buah.get_id_buah())
        self.assertTersimpan()
        self.assertIsNone(self.service.repo_buah.read(buah.get_id_buah()))

    def test_hapus_id_tidak_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException):
            self.service.hapus_catatan_buah("tidak-ada")


class TestDaftarBuah(DasarPanen):
    def test_per_tanggal_hanya_tanggal_itu_urut_nomor_pohon(self):
        self.catat(pohon=self.pohon_7, tanggal_panen="2025-01-15")
        self.catat(pohon=self.pohon_2, tanggal_panen="2025-01-15")
        self.catat(pohon=self.pohon_2, tanggal_panen="2025-01-16")
        hasil = self.service.daftar_buah_per_tanggal("2025-01-15")
        self.assertEqual([b.get_pohon().get_nomor_pohon() for b in hasil], [2, 7])

    def test_per_tanggal_kosong(self):
        self.assertEqual(self.service.daftar_buah_per_tanggal("2025-01-15"), [])

    def test_per_tanggal_tidak_valid_ditolak(self):
        with self.assertRaises(TanggalTidakValidException):
            self.service.daftar_buah_per_tanggal("2025-02-30")

    def test_per_periode_yang_sudah_ditutup(self):
        periode = PeriodePanen("Musim 2025", "2025-01-10", "2025-01-20")
        RepoPeriodePanen(self.conn).create(periode)
        for tanggal in ("2025-01-09", "2025-01-10", "2025-01-20", "2025-01-21"):
            self.catat(tanggal_panen=tanggal)
        hasil = self.service.daftar_buah_per_periode(periode.get_id_periode())
        self.assertEqual([b.get_tanggal_panen() for b in hasil], ["2025-01-10", "2025-01-20"])

    def test_per_periode_aktif_sampai_hari_ini(self):
        periode = PeriodePanen("Musim berjalan", "2025-01-10")
        RepoPeriodePanen(self.conn).create(periode)
        hari_ini = date.today().isoformat()
        self.catat(tanggal_panen="2025-01-09")
        self.catat(tanggal_panen="2025-01-10")
        self.catat(tanggal_panen=hari_ini)
        hasil = self.service.daftar_buah_per_periode(periode.get_id_periode())
        self.assertEqual([b.get_tanggal_panen() for b in hasil], ["2025-01-10", hari_ini])

    def test_per_periode_id_tidak_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException) as cm:
            self.service.daftar_buah_per_periode("tidak-ada")
        self.assertEqual(cm.exception.kolom, "periode_panen")


if __name__ == "__main__":
    unittest.main()
