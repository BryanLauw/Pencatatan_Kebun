import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pencatatan_kebun.db.koneksi import buka_koneksi
from pencatatan_kebun.models import StokPohon
from pencatatan_kebun.repo.stok_pohon import RepoStokPohon
from pencatatan_kebun.services.exception import (
    DataMasihDipakaiException,
    DataSudahAdaException,
    DataTidakDitemukanException,
    NamaKosongException,
    PeriodeBertumpukException,
    PeriodeSudahDitutupException,
    TanggalTidakValidException,
)
from pencatatan_kebun.services.master import MasterService
from pencatatan_kebun.services.periode import PeriodeService


def hari_ini_plus(hari: int) -> str:
    """Tanggal relatif terhadap hari ini, teks YYYY-MM-DD."""
    return (date.today() + timedelta(days=hari)).isoformat()


class DasarPeriode(unittest.TestCase):
    """Persiapan bersama; tidak berisi tes."""

    def setUp(self):
        self.conn = buka_koneksi(":memory:")
        self.addCleanup(self.conn.close)
        self.service = PeriodeService(self.conn)

    def assertTersimpan(self):
        """Service harus commit sendiri: tidak ada transaksi yang tertinggal."""
        self.assertFalse(self.conn.in_transaction)

    def baca(self, periode):
        return self.service.repo_periode.read(periode.get_id_periode())


class TestBukaPeriode(DasarPeriode):
    def test_buka_tersimpan_dan_commit(self):
        periode = self.service.buka_periode("Raya 2025", "2025-01-01", deskripsi="Musim utama")
        self.assertTersimpan()
        hasil = self.baca(periode)
        self.assertEqual(hasil.get_nama(), "Raya 2025")
        self.assertEqual(hasil.get_tanggal_mulai(), "2025-01-01")
        self.assertIsNone(hasil.get_tanggal_selesai())
        self.assertEqual(hasil.get_deskripsi(), "Musim utama")

    def test_buka_dengan_tanggal_selesai(self):
        periode = self.service.buka_periode("Raya 2025", "2025-01-01", "2025-03-31")
        self.assertEqual(self.baca(periode).get_tanggal_selesai(), "2025-03-31")

    def test_spasi_di_tepi_nama_dibuang(self):
        periode = self.service.buka_periode("  Raya 2025 ", "2025-01-01")
        self.assertEqual(self.baca(periode).get_nama(), "Raya 2025")

    def test_nama_kosong_ditolak(self):
        for nama in ("", "   ", None):
            with self.subTest(nama=nama):
                with self.assertRaises(NamaKosongException) as cm:
                    self.service.buka_periode(nama, "2025-01-01")
                self.assertEqual(cm.exception.kolom, "nama_periode")

    def test_nama_ganda_ditolak(self):
        self.service.buka_periode("Raya 2025", "2025-01-01", "2025-03-31")
        for nama in ("Raya 2025", " Raya 2025 "):
            with self.subTest(nama=nama):
                with self.assertRaises(DataSudahAdaException) as cm:
                    self.service.buka_periode(nama, "2025-06-01")
                self.assertEqual(cm.exception.kolom, "nama_periode")

    def test_tanggal_tidak_valid_ditolak(self):
        for mulai, selesai, kolom in (
            ("2025-02-30", None, "tanggal_mulai"),
            ("2025-1-5", None, "tanggal_mulai"),
            ("2025-01-01", "2025-13-01", "tanggal_selesai"),
        ):
            with self.subTest(mulai=mulai, selesai=selesai):
                with self.assertRaises(TanggalTidakValidException) as cm:
                    self.service.buka_periode("Raya", mulai, selesai)
                self.assertEqual(cm.exception.kolom, kolom)

    def test_tanggal_selesai_tidak_setelah_mulai_ditolak(self):
        for selesai in ("2025-01-01", "2024-12-31"):
            with self.subTest(selesai=selesai):
                with self.assertRaises(TanggalTidakValidException) as cm:
                    self.service.buka_periode("Raya", "2025-01-01", selesai)
                self.assertEqual(cm.exception.kolom, "tanggal_selesai")

    def test_menutup_periode_aktif_sebelumnya(self):
        lama = self.service.buka_periode("Raya 2025", "2025-01-01")
        self.service.buka_periode("Raya 2026", "2026-01-01")
        self.assertEqual(self.baca(lama).get_tanggal_selesai(), "2025-12-31")

    def test_bertumpuk_dengan_periode_tertutup_ditolak(self):
        self.service.buka_periode("Raya 2025", "2025-01-01", "2025-03-31")
        for mulai, selesai in (
            ("2025-03-31", None),          # batas sama dihitung bertumpuk
            ("2025-02-01", "2025-02-10"),  # di dalam
            ("2024-12-01", "2025-01-01"),  # menyentuh awal
        ):
            with self.subTest(mulai=mulai, selesai=selesai):
                with self.assertRaises(PeriodeBertumpukException) as cm:
                    self.service.buka_periode("Gadu", mulai, selesai)
                self.assertEqual(cm.exception.kolom, "tanggal_mulai")

    def test_bertumpuk_dengan_tanggal_selesai_di_masa_depan_ditolak(self):
        # Periode yang tanggal selesainya belum lewat tidak dianggap aktif.
        self.service.buka_periode("Raya", hari_ini_plus(-10), hari_ini_plus(30))
        with self.assertRaises(PeriodeBertumpukException):
            self.service.buka_periode("Gadu", hari_ini_plus(5))

    def test_mulai_sebelum_periode_aktif_ditolak(self):
        self.service.buka_periode("Raya 2025", "2025-06-01")
        for mulai in ("2025-06-01", "2025-05-01"):
            with self.subTest(mulai=mulai), self.assertRaises(PeriodeBertumpukException):
                self.service.buka_periode("Gadu", mulai)

    def test_tidak_bertumpuk_boleh(self):
        self.service.buka_periode("Raya 2025", "2025-01-01", "2025-03-31")
        self.service.buka_periode("Gadu 2025", "2025-04-01", "2025-06-30")
        self.assertEqual(len(self.service.daftar_periode()), 2)


class TestTutupPeriode(DasarPeriode):
    def test_tutup_dengan_tanggal_yang_sudah_lewat(self):
        periode = self.service.buka_periode("Raya", "2025-01-01")
        hasil = self.service.tutup_periode(periode.get_id_periode(), "2025-03-31")
        self.assertTersimpan()
        self.assertEqual(hasil.get_tanggal_selesai(), "2025-03-31")
        self.assertEqual(self.baca(periode).get_tanggal_selesai(), "2025-03-31")

    def test_tutup_tanpa_tanggal_jadi_hari_ini(self):
        periode = self.service.buka_periode("Raya", hari_ini_plus(-30))
        for kosong in (None, ""):
            with self.subTest(tanggal=kosong):
                self.conn.execute("UPDATE periode_panen SET tanggal_selesai = NULL")
                self.conn.commit()
                self.service.tutup_periode(periode.get_id_periode(), kosong)
                hasil = self.baca(periode).get_tanggal_selesai()
                self.assertIsInstance(hasil, str)
                self.assertEqual(hasil, date.today().isoformat())

    def test_tutup_tanpa_tanggal_pada_hari_mulai_ditolak(self):
        periode = self.service.buka_periode("Raya", date.today().isoformat())
        with self.assertRaises(TanggalTidakValidException) as cm:
            self.service.tutup_periode(periode.get_id_periode())
        self.assertEqual(cm.exception.kolom, "tanggal_selesai")
        self.assertIsNone(self.baca(periode).get_tanggal_selesai())

    def test_tanggal_tidak_setelah_mulai_ditolak(self):
        periode = self.service.buka_periode("Raya", "2025-01-01")
        for selesai in ("2025-01-01", "2024-12-31"):
            with self.subTest(selesai=selesai), self.assertRaises(TanggalTidakValidException):
                self.service.tutup_periode(periode.get_id_periode(), selesai)

    def test_format_tanggal_salah_ditolak(self):
        periode = self.service.buka_periode("Raya", "2025-01-01")
        with self.assertRaises(TanggalTidakValidException):
            self.service.tutup_periode(periode.get_id_periode(), "2025-02-30")

    def test_sudah_ditutup_ditolak(self):
        periode = self.service.buka_periode("Raya", "2025-01-01", "2025-03-31")
        with self.assertRaises(PeriodeSudahDitutupException):
            self.service.tutup_periode(periode.get_id_periode(), "2025-02-28")
        self.assertEqual(self.baca(periode).get_tanggal_selesai(), "2025-03-31")

    def test_tanggal_selesai_di_masa_depan_dianggap_sudah_ditutup(self):
        periode = self.service.buka_periode("Raya", hari_ini_plus(-10), hari_ini_plus(30))
        with self.assertRaises(PeriodeSudahDitutupException):
            self.service.tutup_periode(periode.get_id_periode(), hari_ini_plus(5))

    def test_id_tidak_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException):
            self.service.tutup_periode("tidak-ada", "2025-03-31")


class TestUbahPeriode(DasarPeriode):
    def test_ubah_semua_kolom(self):
        periode = self.service.buka_periode("Raya", "2025-01-01")
        self.service.ubah_periode(periode.get_id_periode(), " Raya Baru ", "2025-01-05", "2025-04-30", "baru")
        self.assertTersimpan()
        hasil = self.baca(periode)
        self.assertEqual(hasil.get_nama(), "Raya Baru")
        self.assertEqual(hasil.get_tanggal_mulai(), "2025-01-05")
        self.assertEqual(hasil.get_tanggal_selesai(), "2025-04-30")
        self.assertEqual(hasil.get_deskripsi(), "baru")

    def test_ubah_dengan_nama_sendiri(self):
        periode = self.service.buka_periode("Raya", "2025-01-01", "2025-03-31")
        self.service.ubah_periode(periode.get_id_periode(), "Raya", "2025-01-01", "2025-04-30")
        self.assertEqual(self.baca(periode).get_tanggal_selesai(), "2025-04-30")

    def test_ubah_tidak_bertumpuk_dengan_dirinya_sendiri(self):
        periode = self.service.buka_periode("Raya", "2025-01-01", "2025-03-31")
        self.service.ubah_periode(periode.get_id_periode(), "Raya", "2025-02-01", "2025-03-15")
        self.assertEqual(self.baca(periode).get_tanggal_mulai(), "2025-02-01")

    def test_ubah_ke_nama_periode_lain_ditolak(self):
        self.service.buka_periode("Raya", "2025-01-01", "2025-03-31")
        gadu = self.service.buka_periode("Gadu", "2025-04-01", "2025-06-30")
        with self.assertRaises(DataSudahAdaException):
            self.service.ubah_periode(gadu.get_id_periode(), "Raya", "2025-04-01", "2025-06-30")

    def test_ubah_jadi_bertumpuk_ditolak(self):
        self.service.buka_periode("Raya", "2025-01-01", "2025-03-31")
        gadu = self.service.buka_periode("Gadu", "2025-04-01", "2025-06-30")
        with self.assertRaises(PeriodeBertumpukException):
            self.service.ubah_periode(gadu.get_id_periode(), "Gadu", "2025-03-15", "2025-06-30")
        self.assertEqual(self.baca(gadu).get_tanggal_mulai(), "2025-04-01")

    def test_ubah_jadi_aktif_bertumpuk_dengan_periode_sesudahnya_ditolak(self):
        raya = self.service.buka_periode("Raya", "2025-01-01", "2025-03-31")
        self.service.buka_periode("Gadu", "2025-04-01", "2025-06-30")
        with self.assertRaises(PeriodeBertumpukException):
            self.service.ubah_periode(raya.get_id_periode(), "Raya", "2025-01-01", None)

    def test_nama_kosong_ditolak(self):
        periode = self.service.buka_periode("Raya", "2025-01-01")
        for nama in ("", "   ", None):
            with self.subTest(nama=nama), self.assertRaises(NamaKosongException):
                self.service.ubah_periode(periode.get_id_periode(), nama, "2025-01-01", None)

    def test_id_tidak_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException) as cm:
            self.service.ubah_periode("tidak-ada", "Raya", "2025-01-01", None)
        self.assertEqual(cm.exception.kolom, "id_periode")
        self.assertEqual(self.service.daftar_periode(), [])


class TestHapusPeriode(DasarPeriode):
    def test_hapus(self):
        periode = self.service.buka_periode("Raya", "2025-01-01")
        self.service.hapus_periode(periode.get_id_periode())
        self.assertTersimpan()
        self.assertIsNone(self.baca(periode))

    def test_periode_yang_punya_stok_ditolak(self):
        periode = self.service.buka_periode("Raya", "2025-01-01")
        master = MasterService(self.conn)
        varietas = master.tambah_varietas(master.tambah_jenis("Durian"), "Musang King")
        pohon = master.tambah_pohon(varietas, 1)
        RepoStokPohon(self.conn).create(StokPohon(pohon, periode, 5, "2025-01-02"))
        self.conn.commit()
        with self.assertRaises(DataMasihDipakaiException) as cm:
            self.service.hapus_periode(periode.get_id_periode())
        self.assertIn("Raya", cm.exception.pesan)
        self.assertIsNotNone(self.baca(periode))

    def test_id_tidak_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException) as cm:
            self.service.hapus_periode("tidak-ada")
        self.assertEqual(cm.exception.kolom, "id_periode")


class TestBacaPeriode(DasarPeriode):
    def test_periode_aktif(self):
        self.assertIsNone(self.service.periode_aktif())
        self.service.buka_periode("Raya 2025", "2025-01-01", "2025-03-31")
        self.assertIsNone(self.service.periode_aktif())
        aktif = self.service.buka_periode("Gadu 2025", "2025-04-01")
        self.assertEqual(self.service.periode_aktif().get_id_periode(), aktif.get_id_periode())

    def test_periode_aktif_tidak_termasuk_tanggal_selesai_di_masa_depan(self):
        self.service.buka_periode("Raya", hari_ini_plus(-10), hari_ini_plus(30))
        self.assertIsNone(self.service.periode_aktif())

    def test_periode_pada_tanggal(self):
        raya = self.service.buka_periode("Raya", "2025-01-01", "2025-03-31")
        gadu = self.service.buka_periode("Gadu", "2025-06-01")
        for tanggal, harapan in (
            ("2025-01-01", raya),
            ("2025-03-31", raya),
            ("2025-04-15", None),
            ("2024-12-31", None),
            ("2025-06-01", gadu),
        ):
            with self.subTest(tanggal=tanggal):
                hasil = self.service.periode_pada_tanggal(tanggal)
                if harapan is None:
                    self.assertIsNone(hasil)
                else:
                    self.assertEqual(hasil.get_id_periode(), harapan.get_id_periode())

    def test_periode_pada_tanggal_tidak_valid_ditolak(self):
        for tanggal in ("2025-02-30", hari_ini_plus(1)):
            with self.subTest(tanggal=tanggal), self.assertRaises(TanggalTidakValidException):
                self.service.periode_pada_tanggal(tanggal)

    def test_daftar_urut_tanggal_mulai(self):
        self.service.buka_periode("B", "2025-04-01", "2025-06-30")
        self.service.buka_periode("A", "2025-01-01", "2025-03-31")
        self.assertEqual([p.get_nama() for p in self.service.daftar_periode()], ["A", "B"])


if __name__ == "__main__":
    unittest.main()
