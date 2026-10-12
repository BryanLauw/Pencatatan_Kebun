import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pencatatan_kebun.db.koneksi import buka_koneksi
from pencatatan_kebun.models import Buah, JenisTanaman, PeriodePanen, StokPohon, Varietas
from pencatatan_kebun.repo.buah import RepoBuah
from pencatatan_kebun.repo.periode_panen import RepoPeriodePanen
from pencatatan_kebun.repo.stok_pohon import RepoStokPohon
from pencatatan_kebun.services.exception import (
    DataMasihDipakaiException,
    DataSudahAdaException,
    DataTidakDitemukanException,
    NamaKosongException,
    NomorPohonTidakValidException,
)
from pencatatan_kebun.services.master import MasterService


class DasarMaster(unittest.TestCase):
    """Persiapan bersama; tidak berisi tes."""

    def setUp(self):
        self.conn = buka_koneksi(":memory:")
        self.addCleanup(self.conn.close)
        self.service = MasterService(self.conn)

    def catat_buah(self, pohon, keterangan):
        """Simpan satu buah lewat repo agar data master jadi 'dipakai'."""
        RepoBuah(self.conn).create(Buah(pohon, 1.5, keterangan, "2025-01-15"))
        self.conn.commit()

    def varietas_baru(self, nama_jenis="Durian", nama_varietas="Musang King"):
        return self.service.tambah_varietas(self.service.tambah_jenis(nama_jenis), nama_varietas)

    def assertTersimpan(self):
        """Service harus commit sendiri: tidak ada transaksi yang tertinggal."""
        self.assertFalse(self.conn.in_transaction)


class TestJenisTanaman(DasarMaster):
    def test_tambah_tersimpan_dan_commit(self):
        jenis = self.service.tambah_jenis("Durian", "Buah berduri")
        self.assertTersimpan()
        hasil = self.service.repo_jenis.read(jenis.get_id_jenis())
        self.assertEqual(hasil.get_nama_jenis(), "Durian")
        self.assertEqual(hasil.get_deskripsi(), "Buah berduri")

    def test_tambah_spasi_di_tepi_nama_dibuang(self):
        jenis = self.service.tambah_jenis("  Durian ")
        self.assertEqual(self.service.repo_jenis.read(jenis.get_id_jenis()).get_nama_jenis(), "Durian")

    def test_tambah_nama_kosong_ditolak(self):
        for nama in ("", "   ", None):
            with self.subTest(nama=nama):
                with self.assertRaises(NamaKosongException) as cm:
                    self.service.tambah_jenis(nama)
                self.assertEqual(cm.exception.kolom, "nama_jenis")
                self.assertEqual(cm.exception.pesan, "Nama jenis wajib diisi!")

    def test_tambah_nama_ganda_ditolak_tanpa_beda_huruf_dan_spasi(self):
        self.service.tambah_jenis("Durian")
        for nama in ("Durian", "durian", " DURIAN "):
            with self.subTest(nama=nama):
                with self.assertRaises(DataSudahAdaException) as cm:
                    self.service.tambah_jenis(nama)
                self.assertEqual(cm.exception.kolom, "nama_jenis")

    def test_ubah_deskripsi_tanpa_ganti_nama(self):
        jenis = self.service.tambah_jenis("Durian", "lama")
        self.service.ubah_jenis(jenis.get_id_jenis(), "Durian", "baru")
        self.assertTersimpan()
        self.assertEqual(self.service.repo_jenis.read(jenis.get_id_jenis()).get_deskripsi(), "baru")

    def test_ubah_huruf_besar_kecil_nama_sendiri(self):
        jenis = self.service.tambah_jenis("durian")
        self.service.ubah_jenis(jenis.get_id_jenis(), "Durian")
        self.assertEqual(self.service.repo_jenis.read(jenis.get_id_jenis()).get_nama_jenis(), "Durian")

    def test_ubah_ke_nama_jenis_lain_ditolak(self):
        self.service.tambah_jenis("Durian")
        mangga = self.service.tambah_jenis("Mangga")
        with self.assertRaises(DataSudahAdaException):
            self.service.ubah_jenis(mangga.get_id_jenis(), "durian")

    def test_ubah_id_tidak_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException):
            self.service.ubah_jenis("tidak-ada", "Durian")

    def test_ubah_id_tidak_ada_dicek_sebelum_nama(self):
        with self.assertRaises(DataTidakDitemukanException):
            self.service.ubah_jenis("tidak-ada", "")

    def test_hapus(self):
        jenis = self.service.tambah_jenis("Durian")
        self.service.hapus_jenis(jenis.get_id_jenis())
        self.assertTersimpan()
        self.assertIsNone(self.service.repo_jenis.read(jenis.get_id_jenis()))

    def test_hapus_jenis_yang_punya_varietas_ditolak(self):
        jenis = self.service.tambah_jenis("Durian")
        self.service.tambah_varietas(jenis, "Musang King")
        with self.assertRaises(DataMasihDipakaiException) as cm:
            self.service.hapus_jenis(jenis.get_id_jenis())
        self.assertIn("Durian", cm.exception.pesan)
        self.assertIsNotNone(self.service.repo_jenis.read(jenis.get_id_jenis()))

    def test_hapus_id_tidak_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException):
            self.service.hapus_jenis("tidak-ada")

    def test_daftar_urut_nama(self):
        for nama in ("Mangga", "Durian", "Alpukat"):
            self.service.tambah_jenis(nama)
        self.assertEqual([j.get_nama_jenis() for j in self.service.daftar_jenis()],
                         ["Alpukat", "Durian", "Mangga"])


class TestVarietas(DasarMaster):
    def setUp(self):
        super().setUp()
        self.durian = self.service.tambah_jenis("Durian")
        self.mangga = self.service.tambah_jenis("Mangga")

    def test_tambah_tersimpan_beserta_jenis(self):
        varietas = self.service.tambah_varietas(self.durian, " Musang King ", "Daging kuning")
        self.assertTersimpan()
        hasil = self.service.repo_varietas.read(varietas.get_id_varietas())
        self.assertEqual(hasil.get_nama_varietas(), "Musang King")
        self.assertEqual(hasil.get_jenis().get_id_jenis(), self.durian.get_id_jenis())

    def test_tambah_nama_kosong_ditolak(self):
        for nama in ("", "   ", None):
            with self.subTest(nama=nama):
                with self.assertRaises(NamaKosongException) as cm:
                    self.service.tambah_varietas(self.durian, nama)
                self.assertEqual(cm.exception.kolom, "nama_varietas")

    def test_nama_sama_di_jenis_lain_boleh(self):
        self.service.tambah_varietas(self.durian, "Lokal")
        self.service.tambah_varietas(self.mangga, "Lokal")
        self.assertEqual(len(self.service.daftar_varietas()), 2)

    def test_nama_ganda_di_jenis_sama_ditolak(self):
        self.service.tambah_varietas(self.durian, "Musang King")
        with self.assertRaises(DataSudahAdaException) as cm:
            self.service.tambah_varietas(self.durian, "musang king")
        self.assertEqual(cm.exception.kolom, "nama_varietas")

    def test_jenis_tidak_ada_di_database_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException) as cm:
            self.service.tambah_varietas(JenisTanaman("Rambutan"), "Binjai")
        self.assertEqual(cm.exception.kolom, "id_jenis")

    def test_ubah_deskripsi_tanpa_ganti_nama(self):
        varietas = self.service.tambah_varietas(self.durian, "Musang King", "lama")
        self.service.ubah_varietas(varietas.get_id_varietas(), self.durian, "Musang King", "baru")
        self.assertTersimpan()
        self.assertEqual(self.service.repo_varietas.read(varietas.get_id_varietas()).get_deskripsi(), "baru")

    def test_ubah_pindah_jenis(self):
        varietas = self.service.tambah_varietas(self.durian, "Lokal")
        self.service.ubah_varietas(varietas.get_id_varietas(), self.mangga, "Lokal")
        hasil = self.service.repo_varietas.read(varietas.get_id_varietas())
        self.assertEqual(hasil.get_jenis().get_id_jenis(), self.mangga.get_id_jenis())

    def test_ubah_pindah_ke_jenis_yang_sudah_punya_nama_itu_ditolak(self):
        self.service.tambah_varietas(self.mangga, "Lokal")
        varietas = self.service.tambah_varietas(self.durian, "Lokal")
        with self.assertRaises(DataSudahAdaException):
            self.service.ubah_varietas(varietas.get_id_varietas(), self.mangga, "Lokal")

    def test_ubah_id_tidak_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException) as cm:
            self.service.ubah_varietas("tidak-ada", self.durian, "")
        self.assertEqual(cm.exception.kolom, "id_varietas")

    def test_hapus(self):
        varietas = self.service.tambah_varietas(self.durian, "Musang King")
        self.service.hapus_varietas(varietas.get_id_varietas())
        self.assertTersimpan()
        self.assertIsNone(self.service.repo_varietas.read(varietas.get_id_varietas()))

    def test_hapus_varietas_yang_dipakai_pohon_ditolak(self):
        varietas = self.service.tambah_varietas(self.durian, "Musang King")
        self.service.tambah_pohon(varietas, 1)
        with self.assertRaises(DataMasihDipakaiException) as cm:
            self.service.hapus_varietas(varietas.get_id_varietas())
        self.assertIn("Musang King", cm.exception.pesan)

    def test_hapus_id_tidak_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException):
            self.service.hapus_varietas("tidak-ada")

    def test_daftar_per_jenis_hanya_jenis_itu_dan_berupa_objek_varietas(self):
        self.service.tambah_varietas(self.durian, "Musang King")
        self.service.tambah_varietas(self.durian, "Bawor")
        self.service.tambah_varietas(self.mangga, "Harum Manis")
        hasil = self.service.daftar_varietas(self.durian)
        self.assertEqual([v.get_nama_varietas() for v in hasil], ["Bawor", "Musang King"])
        self.assertEqual(hasil[0].get_jenis().get_nama_jenis(), "Durian")

    def test_daftar_semua_urut_jenis_lalu_nama(self):
        self.service.tambah_varietas(self.mangga, "Harum Manis")
        self.service.tambah_varietas(self.durian, "Musang King")
        self.service.tambah_varietas(self.durian, "Bawor")
        self.assertEqual([v.get_nama_varietas() for v in self.service.daftar_varietas()],
                         ["Bawor", "Musang King", "Harum Manis"])


class TestPohon(DasarMaster):
    def setUp(self):
        super().setUp()
        self.durian = self.service.tambah_jenis("Durian")
        self.musang_king = self.service.tambah_varietas(self.durian, "Musang King")
        self.montong = self.service.tambah_varietas(self.durian, "Montong")

    def test_tambah_tersimpan_beserta_varietas(self):
        pohon = self.service.tambah_pohon(self.musang_king, 7)
        self.assertTersimpan()
        hasil = self.service.repo_pohon.read(pohon.get_id_pohon())
        self.assertEqual(hasil.get_nomor_pohon(), 7)
        self.assertEqual(hasil.get_varietas().get_id_varietas(), self.musang_king.get_id_varietas())
        self.assertEqual(hasil.get_varietas().get_jenis().get_nama_jenis(), "Durian")

    def test_nomor_tidak_valid_ditolak(self):
        for nomor in (0, -1, 1.5, "7", None, True):
            with self.subTest(nomor=nomor):
                with self.assertRaises(NomorPohonTidakValidException) as cm:
                    self.service.tambah_pohon(self.musang_king, nomor)
                self.assertEqual(cm.exception.kolom, "nomor_pohon")

    def test_varietas_tidak_ada_di_database_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException) as cm:
            self.service.tambah_pohon(Varietas("Bawor", self.durian), 1)
        self.assertEqual(cm.exception.kolom, "id_varietas")
        self.assertEqual(self.service.daftar_pohon(), [])

    def test_nomor_ganda_di_varietas_sama_ditolak(self):
        self.service.tambah_pohon(self.musang_king, 7)
        with self.assertRaises(DataSudahAdaException) as cm:
            self.service.tambah_pohon(self.musang_king, 7)
        self.assertEqual(cm.exception.kolom, "nomor_pohon")
        self.assertIn("Musang King", cm.exception.pesan)

    def test_nomor_sama_di_varietas_lain_boleh(self):
        self.service.tambah_pohon(self.musang_king, 7)
        self.service.tambah_pohon(self.montong, 7)
        self.assertEqual(len(self.service.daftar_pohon()), 2)

    def test_ubah_dengan_nomor_sendiri(self):
        pohon = self.service.tambah_pohon(self.musang_king, 7)
        self.service.ubah_pohon(pohon.get_id_pohon(), self.musang_king, 7)
        self.assertTersimpan()

    def test_ubah_nomor(self):
        pohon = self.service.tambah_pohon(self.musang_king, 7)
        self.service.ubah_pohon(pohon.get_id_pohon(), self.musang_king, 8)
        self.assertEqual(self.service.repo_pohon.read(pohon.get_id_pohon()).get_nomor_pohon(), 8)

    def test_ubah_pindah_varietas(self):
        pohon = self.service.tambah_pohon(self.musang_king, 7)
        self.service.ubah_pohon(pohon.get_id_pohon(), self.montong, 7)
        hasil = self.service.repo_pohon.read(pohon.get_id_pohon())
        self.assertEqual(hasil.get_varietas().get_id_varietas(), self.montong.get_id_varietas())

    def test_ubah_ke_nomor_pohon_lain_ditolak(self):
        self.service.tambah_pohon(self.musang_king, 7)
        pohon = self.service.tambah_pohon(self.musang_king, 8)
        with self.assertRaises(DataSudahAdaException):
            self.service.ubah_pohon(pohon.get_id_pohon(), self.musang_king, 7)

    def test_ubah_pindah_ke_varietas_yang_sudah_punya_nomor_itu_ditolak(self):
        self.service.tambah_pohon(self.montong, 7)
        pohon = self.service.tambah_pohon(self.musang_king, 7)
        with self.assertRaises(DataSudahAdaException):
            self.service.ubah_pohon(pohon.get_id_pohon(), self.montong, 7)

    def test_ubah_ke_varietas_yang_tidak_ada_ditolak(self):
        pohon = self.service.tambah_pohon(self.musang_king, 7)
        with self.assertRaises(DataTidakDitemukanException) as cm:
            self.service.ubah_pohon(pohon.get_id_pohon(), Varietas("Bawor", self.durian), 7)
        self.assertEqual(cm.exception.kolom, "id_varietas")

    def test_ubah_id_tidak_ada_dicek_sebelum_nomor(self):
        with self.assertRaises(DataTidakDitemukanException):
            self.service.ubah_pohon("tidak-ada", self.musang_king, 0)

    def test_hapus(self):
        pohon = self.service.tambah_pohon(self.musang_king, 7)
        self.service.hapus_pohon(pohon.get_id_pohon())
        self.assertTersimpan()
        self.assertIsNone(self.service.repo_pohon.read(pohon.get_id_pohon()))

    def test_hapus_pohon_yang_dipakai_buah_ditolak(self):
        pohon = self.service.tambah_pohon(self.musang_king, 7)
        self.catat_buah(pohon, self.service.tambah_keterangan("Baik"))
        with self.assertRaises(DataMasihDipakaiException) as cm:
            self.service.hapus_pohon(pohon.get_id_pohon())
        self.assertIn("Musang King 7", cm.exception.pesan)

    def test_hapus_pohon_yang_punya_stok_ditolak(self):
        pohon = self.service.tambah_pohon(self.musang_king, 7)
        periode = PeriodePanen("Raya 2025", "2025-01-01")
        RepoPeriodePanen(self.conn).create(periode)
        RepoStokPohon(self.conn).create(StokPohon(pohon, periode, 5, "2025-01-02"))
        self.conn.commit()
        with self.assertRaises(DataMasihDipakaiException):
            self.service.hapus_pohon(pohon.get_id_pohon())

    def test_hapus_id_tidak_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException):
            self.service.hapus_pohon("tidak-ada")

    def test_daftar_per_varietas_urut_nomor(self):
        for nomor in (10, 2, 7):
            self.service.tambah_pohon(self.musang_king, nomor)
        self.service.tambah_pohon(self.montong, 1)
        hasil = self.service.daftar_pohon(self.musang_king)
        self.assertEqual([p.get_nomor_pohon() for p in hasil], [2, 7, 10])
        self.assertEqual(hasil[0].get_varietas().get_nama_varietas(), "Musang King")

    def test_daftar_semua_urut_varietas_lalu_nomor(self):
        self.service.tambah_pohon(self.musang_king, 2)
        self.service.tambah_pohon(self.montong, 5)
        self.service.tambah_pohon(self.montong, 1)
        self.assertEqual(
            [(p.get_varietas().get_nama_varietas(), p.get_nomor_pohon())
             for p in self.service.daftar_pohon()],
            [("Montong", 1), ("Montong", 5), ("Musang King", 2)])


class TestKeteranganBuah(DasarMaster):
    def test_tambah_tersimpan(self):
        keterangan = self.service.tambah_keterangan(" Baik ", "Layak jual")
        self.assertTersimpan()
        hasil = self.service.repo_keterangan.read(keterangan.get_id_keterangan())
        self.assertEqual(hasil.get_nama_keterangan(), "Baik")
        self.assertEqual(hasil.get_deskripsi(), "Layak jual")

    def test_tambah_nama_kosong_ditolak(self):
        for nama in ("", "   ", None):
            with self.subTest(nama=nama):
                with self.assertRaises(NamaKosongException) as cm:
                    self.service.tambah_keterangan(nama)
                self.assertEqual(cm.exception.kolom, "nama_keterangan")
                self.assertEqual(cm.exception.pesan, "Nama keterangan wajib diisi!")

    def test_tambah_nama_ganda_ditolak(self):
        self.service.tambah_keterangan("Baik")
        with self.assertRaises(DataSudahAdaException):
            self.service.tambah_keterangan("BAIK")

    def test_ubah_deskripsi_tanpa_ganti_nama(self):
        keterangan = self.service.tambah_keterangan("Baik", "lama")
        self.service.ubah_keterangan(keterangan.get_id_keterangan(), "Baik", "baru")
        self.assertTersimpan()
        self.assertEqual(
            self.service.repo_keterangan.read(keterangan.get_id_keterangan()).get_deskripsi(), "baru")

    def test_ubah_ke_nama_keterangan_lain_ditolak(self):
        self.service.tambah_keterangan("Baik")
        busuk = self.service.tambah_keterangan("Busuk")
        with self.assertRaises(DataSudahAdaException):
            self.service.ubah_keterangan(busuk.get_id_keterangan(), "baik")

    def test_ubah_id_tidak_ada_dicek_sebelum_nama(self):
        with self.assertRaises(DataTidakDitemukanException):
            self.service.ubah_keterangan("tidak-ada", "")

    def test_hapus(self):
        keterangan = self.service.tambah_keterangan("Baik")
        self.service.hapus_keterangan(keterangan.get_id_keterangan())
        self.assertTersimpan()
        self.assertIsNone(self.service.repo_keterangan.read(keterangan.get_id_keterangan()))

    def test_hapus_keterangan_yang_dipakai_buah_ditolak(self):
        keterangan = self.service.tambah_keterangan("Baik")
        self.catat_buah(self.service.tambah_pohon(self.varietas_baru(), 1), keterangan)
        with self.assertRaises(DataMasihDipakaiException) as cm:
            self.service.hapus_keterangan(keterangan.get_id_keterangan())
        self.assertIn("Baik", cm.exception.pesan)

    def test_hapus_id_tidak_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException):
            self.service.hapus_keterangan("tidak-ada")

    def test_daftar_urut_nama(self):
        for nama in ("Busuk", "Baik", "Cacat"):
            self.service.tambah_keterangan(nama)
        self.assertEqual([k.get_nama_keterangan() for k in self.service.daftar_keterangan()],
                         ["Baik", "Busuk", "Cacat"])


if __name__ == "__main__":
    unittest.main()
