import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pencatatan_kebun.db.koneksi import buka_koneksi
from pencatatan_kebun.models import Buah, JenisTanaman, KeteranganBuah, PeriodePanen, Pohon, Varietas
from pencatatan_kebun.repo.buah import RepoBuah
from pencatatan_kebun.repo.jenis_tanaman import RepoJenisTanaman
from pencatatan_kebun.repo.keterangan_buah import RepoKeteranganBuah
from pencatatan_kebun.repo.periode_panen import RepoPeriodePanen
from pencatatan_kebun.repo.pohon import RepoPohon
from pencatatan_kebun.repo.varietas import RepoVarietas


class DasarRepo(unittest.TestCase):
    """Persiapan bersama; tidak berisi tes."""

    def setUp(self):
        self.conn = buka_koneksi(":memory:")
        self.addCleanup(self.conn.close)
        self.repo_jenis = RepoJenisTanaman(self.conn)
        self.repo_varietas = RepoVarietas(self.conn)
        self.repo_pohon = RepoPohon(self.conn)
        self.repo_keterangan = RepoKeteranganBuah(self.conn)
        self.repo_buah = RepoBuah(self.conn)
        self.repo_periode = RepoPeriodePanen(self.conn)

        self.jenis = JenisTanaman("Durian", "Buah berduri")
        self.varietas = Varietas("Musang King", self.jenis, "Daging kuning")
        self.pohon = Pohon(7)
        self.baik = KeteranganBuah("Baik", "Layak jual")

    def simpan_induk(self):
        self.repo_jenis.create(self.jenis)
        self.repo_varietas.create(self.varietas)
        self.repo_pohon.create(self.pohon)
        self.repo_keterangan.create(self.baik)

    def buah_baru(self, **ubah):
        data = dict(pohon=self.pohon, varietas=self.varietas, bobot=1.25,
                    keterangan=self.baik, tanggal_panen="2026-01-15")
        data.update(ubah)
        return Buah(**data)


class TestRepo(DasarRepo):
    # ---- ambil id yang tidak ada ----

    def test_read_id_yang_tidak_ada_mengembalikan_none(self):
        for repo in (self.repo_jenis, self.repo_varietas, self.repo_pohon,
                     self.repo_keterangan, self.repo_buah, self.repo_periode):
            self.assertIsNone(repo.read("tidak-ada"), type(repo).__name__)

    # ---- jenis_tanaman ----

    def test_jenis_tanaman_create_dan_read(self):
        self.repo_jenis.create(self.jenis)
        hasil = self.repo_jenis.read(self.jenis.get_id_jenis())
        self.assertEqual(hasil.get_id_jenis(), self.jenis.get_id_jenis())
        self.assertEqual(hasil.get_nama_jenis(), "Durian")
        self.assertEqual(hasil.get_deskripsi(), "Buah berduri")

    def test_jenis_tanaman_deskripsi_kosong_tetap_kosong(self):
        jenis = JenisTanaman("Mangga")
        self.repo_jenis.create(jenis)
        self.assertEqual(self.repo_jenis.read(jenis.get_id_jenis()).get_deskripsi(), "")

    def test_jenis_tanaman_id_ganda_ditolak(self):
        self.repo_jenis.create(self.jenis)
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo_jenis.create(JenisTanaman("Mangga", id_jenis=self.jenis.get_id_jenis()))

    # ---- varietas ----

    def test_varietas_create_dan_read_beserta_jenis(self):
        self.repo_jenis.create(self.jenis)
        self.repo_varietas.create(self.varietas)
        hasil = self.repo_varietas.read(self.varietas.get_id_varietas())
        self.assertEqual(hasil.get_id_varietas(), self.varietas.get_id_varietas())
        self.assertEqual(hasil.get_nama_varietas(), "Musang King")
        self.assertEqual(hasil.get_deskripsi(), "Daging kuning")
        self.assertEqual(hasil.get_jenis().get_id_jenis(), self.jenis.get_id_jenis())
        self.assertEqual(hasil.get_jenis().get_nama_jenis(), "Durian")

    def test_varietas_ditolak_jika_jenis_belum_disimpan(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo_varietas.create(self.varietas)

    # ---- pohon ----

    def test_pohon_create_dan_read(self):
        self.repo_pohon.create(self.pohon)
        hasil = self.repo_pohon.read(self.pohon.get_id_pohon())
        self.assertEqual(hasil.get_id_pohon(), self.pohon.get_id_pohon())
        self.assertEqual(hasil.get_nomor_pohon(), 7)

    def test_pohon_nomor_ganda_ditolak(self):
        self.repo_pohon.create(self.pohon)
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo_pohon.create(Pohon(7))

    # ---- keterangan_buah ----

    def test_keterangan_buah_create_dan_read(self):
        self.repo_keterangan.create(self.baik)
        hasil = self.repo_keterangan.read(self.baik.get_id_keterangan())
        self.assertEqual(hasil.get_id_keterangan(), self.baik.get_id_keterangan())
        self.assertEqual(hasil.get_nama_keterangan(), "Baik")
        self.assertEqual(hasil.get_deskripsi(), "Layak jual")

    def test_keterangan_buah_nama_ganda_ditolak(self):
        self.repo_keterangan.create(self.baik)
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo_keterangan.create(KeteranganBuah("BAIK"))

    # ---- buah ----

    def test_buah_create_dan_read_beserta_relasi(self):
        self.simpan_induk()
        buah = self.buah_baru()
        self.repo_buah.create(buah)
        hasil = self.repo_buah.read(buah.get_id_buah())
        self.assertEqual(hasil.get_id_buah(), buah.get_id_buah())
        self.assertEqual(hasil.get_bobot(), 1.25)
        self.assertEqual(hasil.get_tanggal_panen(), "2026-01-15")
        self.assertEqual(hasil.get_pohon().get_id_pohon(), self.pohon.get_id_pohon())
        self.assertEqual(hasil.get_pohon().get_nomor_pohon(), 7)
        self.assertEqual(hasil.get_varietas().get_id_varietas(), self.varietas.get_id_varietas())
        self.assertEqual(hasil.get_varietas().get_jenis().get_id_jenis(), self.jenis.get_id_jenis())
        self.assertEqual(hasil.get_keterangan().get_id_keterangan(), self.baik.get_id_keterangan())

    def test_buah_ditolak_jika_induk_belum_disimpan(self):
        self.simpan_induk()
        kasus = {
            "pohon": dict(pohon=Pohon(99)),
            "varietas": dict(varietas=Varietas("D24", self.jenis)),
            "keterangan": dict(keterangan=KeteranganBuah("Busuk")),
        }
        for nama, ubah in kasus.items():
            with self.assertRaises(sqlite3.IntegrityError, msg=nama):
                self.repo_buah.create(self.buah_baru(**ubah))

    def test_buah_ditolak_jika_data_tidak_valid(self):
        self.simpan_induk()
        kasus = {
            "bobot nol": dict(bobot=0),
            "tanggal salah": dict(tanggal_panen="15-01-2026"),
            "tanggal tidak ada": dict(tanggal_panen="2026-02-30"),
        }
        for nama, ubah in kasus.items():
            with self.assertRaises(sqlite3.IntegrityError, msg=nama):
                self.repo_buah.create(self.buah_baru(**ubah))

    # ---- periode_panen ----

    def test_periode_panen_create_dan_read(self):
        periode = PeriodePanen("Raya 2026", "2026-01-01", "2026-03-31", "Panen utama")
        self.repo_periode.create(periode)
        hasil = self.repo_periode.read(periode.get_id_periode())
        self.assertEqual(hasil.get_id_periode(), periode.get_id_periode())
        self.assertEqual(hasil.get_nama(), "Raya 2026")
        self.assertEqual(hasil.get_tanggal_mulai(), "2026-01-01")
        self.assertEqual(hasil.get_tanggal_selesai(), "2026-03-31")
        self.assertEqual(hasil.get_deskripsi(), "Panen utama")

    def test_periode_panen_belum_selesai_kembali_none(self):
        periode = PeriodePanen("Raya 2026", "2026-01-01", None)
        self.repo_periode.create(periode)
        hasil = self.repo_periode.read(periode.get_id_periode())
        self.assertIsNone(hasil.get_tanggal_selesai())
        self.assertTrue(hasil.is_active())

    def test_periode_panen_baru_menutup_periode_terbuka(self):
        lama = PeriodePanen("Lama", "2026-01-01", None)
        baru = PeriodePanen("Baru", "2026-06-01", None)
        self.repo_periode.create(lama)
        self.repo_periode.create(baru)
        self.assertEqual(
            self.repo_periode.read(lama.get_id_periode()).get_tanggal_selesai(), "2026-05-31")
        self.assertIsNone(self.repo_periode.read(baru.get_id_periode()).get_tanggal_selesai())

    def test_periode_panen_tumpang_tindih_ditolak(self):
        self.repo_periode.create(PeriodePanen("A", "2026-01-01", "2026-03-31"))
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo_periode.create(PeriodePanen("B", "2026-03-01", "2026-05-31"))


class TestRepoLanjutan(DasarRepo):
    """ambil_semua, pencarian, hapus, dan perbarui."""

    def id_dari(self, objek_list, getter):
        return {getattr(o, getter)() for o in objek_list}

    # ---- ambil_semua ----

    def test_read_all_kosong(self):
        for repo in (self.repo_jenis, self.repo_varietas, self.repo_pohon,
                     self.repo_keterangan, self.repo_buah, self.repo_periode):
            self.assertEqual(repo.read_all(), [], type(repo).__name__)

    def test_read_all_mengembalikan_semua_baris(self):
        self.simpan_induk()
        mangga = JenisTanaman("Mangga")
        self.repo_jenis.create(mangga)
        d24 = Varietas("D24", self.jenis)
        self.repo_varietas.create(d24)
        pohon_2 = Pohon(8)
        self.repo_pohon.create(pohon_2)
        busuk = KeteranganBuah("Busuk")
        self.repo_keterangan.create(busuk)
        b1, b2 = self.buah_baru(), self.buah_baru(pohon=pohon_2, varietas=d24, keterangan=busuk)
        self.repo_buah.create(b1)
        self.repo_buah.create(b2)
        p1 = PeriodePanen("A", "2026-01-01", "2026-03-31")
        p2 = PeriodePanen("B", "2026-06-01", None)
        self.repo_periode.create(p1)
        self.repo_periode.create(p2)

        kasus = [
            (self.repo_jenis, "get_id_jenis", [self.jenis, mangga]),
            (self.repo_varietas, "get_id_varietas", [self.varietas, d24]),
            (self.repo_pohon, "get_id_pohon", [self.pohon, pohon_2]),
            (self.repo_keterangan, "get_id_keterangan", [self.baik, busuk]),
            (self.repo_buah, "get_id_buah", [b1, b2]),
            (self.repo_periode, "get_id_periode", [p1, p2]),
        ]
        for repo, getter, harapan in kasus:
            self.assertEqual(self.id_dari(repo.read_all(), getter),
                             self.id_dari(harapan, getter), type(repo).__name__)

    def test_read_all_membawa_relasi(self):
        self.simpan_induk()
        self.repo_buah.create(self.buah_baru())
        varietas = self.repo_varietas.read_all()[0]
        self.assertEqual(varietas.get_jenis().get_id_jenis(), self.jenis.get_id_jenis())
        buah = self.repo_buah.read_all()[0]
        self.assertEqual(buah.get_pohon().get_id_pohon(), self.pohon.get_id_pohon())
        self.assertEqual(buah.get_varietas().get_id_varietas(), self.varietas.get_id_varietas())
        self.assertEqual(buah.get_keterangan().get_id_keterangan(), self.baik.get_id_keterangan())

    # ---- cari berdasarkan nama / nomor ----

    def test_read_by_name_tanpa_membedakan_huruf(self):
        self.simpan_induk()
        kasus = [
            (self.repo_jenis.read_by_name("durian"), "get_id_jenis", self.jenis),
            (self.repo_varietas.read_by_name("MUSANG KING", self.jenis), "get_id_varietas",
             self.varietas),
            (self.repo_keterangan.read_by_name("baik"), "get_id_keterangan", self.baik),
        ]
        for hasil, getter, harapan in kasus:
            self.assertEqual(getattr(hasil, getter)(), getattr(harapan, getter)(), getter)

    def test_read_by_name_varietas_membawa_jenis(self):
        self.simpan_induk()
        hasil = self.repo_varietas.read_by_name("Musang King", self.jenis)
        self.assertEqual(hasil.get_jenis().get_nama_jenis(), "Durian")

    def test_read_by_name_varietas_sesuai_jenis(self):
        self.simpan_induk()
        mangga = JenisTanaman("Mangga")
        self.repo_jenis.create(mangga)
        lokal_durian = Varietas("Lokal", self.jenis)
        lokal_mangga = Varietas("Lokal", mangga)
        self.repo_varietas.create(lokal_durian)
        self.repo_varietas.create(lokal_mangga)
        self.assertEqual(
            self.repo_varietas.read_by_name("Lokal", self.jenis).get_id_varietas(),
            lokal_durian.get_id_varietas())
        self.assertEqual(
            self.repo_varietas.read_by_name("Lokal", mangga).get_id_varietas(),
            lokal_mangga.get_id_varietas())

    def test_read_by_name_varietas_di_jenis_lain_tidak_ditemukan(self):
        self.simpan_induk()
        mangga = JenisTanaman("Mangga")
        self.repo_jenis.create(mangga)
        self.assertIsNone(self.repo_varietas.read_by_name("Musang King", mangga))

    def test_read_by_name_yang_tidak_ada(self):
        self.simpan_induk()
        self.assertIsNone(self.repo_jenis.read_by_name("Rambutan"))
        self.assertIsNone(self.repo_varietas.read_by_name("Montong", self.jenis))
        self.assertIsNone(self.repo_keterangan.read_by_name("Cacat"))

    def test_read_by_number_pohon(self):
        self.repo_pohon.create(self.pohon)
        self.assertEqual(
            self.repo_pohon.read_by_number(7).get_id_pohon(), self.pohon.get_id_pohon())
        self.assertIsNone(self.repo_pohon.read_by_number(99))

    def test_read_by_names(self):
        self.simpan_induk()
        mangga = JenisTanaman("Mangga")
        self.repo_jenis.create(mangga)
        self.repo_jenis.create(JenisTanaman("Alpukat"))
        hasil = self.repo_jenis.read_by_names(["Durian", "mangga", "Rambutan"])
        self.assertEqual(self.id_dari(hasil, "get_id_jenis"),
                         {self.jenis.get_id_jenis(), mangga.get_id_jenis()})

        d24 = Varietas("D24", self.jenis)
        self.repo_varietas.create(d24)
        hasil = self.repo_varietas.read_by_names(["Musang King", "D24"])
        self.assertEqual(self.id_dari(hasil, "get_id_varietas"),
                         {self.varietas.get_id_varietas(), d24.get_id_varietas()})

        busuk = KeteranganBuah("Busuk")
        self.repo_keterangan.create(busuk)
        hasil = self.repo_keterangan.read_by_names(["Baik", "Busuk"])
        self.assertEqual(self.id_dari(hasil, "get_id_keterangan"),
                         {self.baik.get_id_keterangan(), busuk.get_id_keterangan()})

    def test_read_by_numbers(self):
        pohon_8, pohon_9 = Pohon(8), Pohon(9)
        for pohon in (self.pohon, pohon_8, pohon_9):
            self.repo_pohon.create(pohon)
        hasil = self.repo_pohon.read_by_numbers([7, 9, 100])
        self.assertEqual(self.id_dari(hasil, "get_id_pohon"),
                         {self.pohon.get_id_pohon(), pohon_9.get_id_pohon()})

    def test_pencarian_banyak_dengan_daftar_kosong(self):
        self.simpan_induk()
        self.assertEqual(self.repo_jenis.read_by_names([]), [])
        self.assertEqual(self.repo_varietas.read_by_names([]), [])
        self.assertEqual(self.repo_keterangan.read_by_names([]), [])
        self.assertEqual(self.repo_pohon.read_by_numbers([]), [])
        self.assertEqual(self.repo_buah.read_by_harvest_dates([]), [])

    # ---- buah berdasarkan tanggal panen ----

    def test_buah_berdasarkan_tanggal_panen(self):
        self.simpan_induk()
        b1 = self.buah_baru(tanggal_panen="2026-01-15")
        b2 = self.buah_baru(tanggal_panen="2026-01-15")
        b3 = self.buah_baru(tanggal_panen="2026-01-16")
        b4 = self.buah_baru(tanggal_panen="2026-01-17")
        for buah in (b1, b2, b3, b4):
            self.repo_buah.create(buah)

        hasil = self.repo_buah.read_by_harvest_date("2026-01-15")
        self.assertEqual(self.id_dari(hasil, "get_id_buah"),
                         {b1.get_id_buah(), b2.get_id_buah()})
        self.assertEqual(hasil[0].get_varietas().get_id_varietas(),
                         self.varietas.get_id_varietas())
        self.assertEqual(self.repo_buah.read_by_harvest_date("2026-02-01"), [])

        hasil = self.repo_buah.read_by_harvest_dates(
            ["2026-01-15", "2026-01-17"])
        self.assertEqual(self.id_dari(hasil, "get_id_buah"),
                         {b1.get_id_buah(), b2.get_id_buah(), b4.get_id_buah()})

    # ---- periode_panen: ambil_rentang ----

    def nama_periode_rentang(self, mulai, selesai):
        return [p.get_nama() for p in self.repo_periode.read_by_range(mulai, selesai)]

    def test_read_by_range_mengambil_periode_yang_bersinggungan(self):
        self.repo_periode.create(PeriodePanen("Lama", "2025-01-01", "2025-03-31"))
        self.repo_periode.create(PeriodePanen("Awal", "2026-01-01", "2026-03-31"))
        self.repo_periode.create(PeriodePanen("Tengah", "2026-04-01", "2026-05-31"))
        self.repo_periode.create(PeriodePanen("Aktif", "2026-06-01", None))

        self.assertEqual(self.nama_periode_rentang("2026-01-01", "2026-12-31"),
                         ["Awal", "Tengah", "Aktif"])
        self.assertEqual(self.nama_periode_rentang("2026-02-01", "2026-04-15"),
                         ["Awal", "Tengah"])
        self.assertEqual(self.nama_periode_rentang("2026-04-10", "2026-04-20"), ["Tengah"])
        self.assertEqual(self.nama_periode_rentang("2025-04-01", "2025-12-31"), [])

    def test_read_by_range_batas_dihitung_bersinggungan(self):
        self.repo_periode.create(PeriodePanen("Awal", "2026-01-01", "2026-03-31"))
        self.assertEqual(self.nama_periode_rentang("2026-03-31", "2026-04-30"), ["Awal"])
        self.assertEqual(self.nama_periode_rentang("2025-12-01", "2026-01-01"), ["Awal"])
        self.assertEqual(self.nama_periode_rentang("2026-04-01", "2026-04-30"), [])

    def test_read_by_range_periode_aktif_ikut_setelah_mulai(self):
        self.repo_periode.create(PeriodePanen("Aktif", "2026-06-01", None))
        self.assertEqual(self.nama_periode_rentang("2030-01-01", "2030-12-31"), ["Aktif"])
        self.assertEqual(self.nama_periode_rentang("2026-01-01", "2026-05-31"), [])

    def test_read_by_range_urut_berdasarkan_tanggal_mulai(self):
        self.repo_periode.create(PeriodePanen("Kedua", "2026-04-01", "2026-05-31"))
        self.repo_periode.create(PeriodePanen("Pertama", "2026-01-01", "2026-03-31"))
        self.assertEqual(self.nama_periode_rentang("2026-01-01", "2026-12-31"),
                         ["Pertama", "Kedua"])

    # ---- urutan hasil ----

    def test_urutan_jenis_dan_keterangan_berdasarkan_nama(self):
        for nama in ("Mangga", "alpukat", "Durian"):
            self.repo_jenis.create(JenisTanaman(nama))
            self.repo_keterangan.create(KeteranganBuah(nama))
        harapan = ["alpukat", "Durian", "Mangga"]
        self.assertEqual([j.get_nama_jenis() for j in self.repo_jenis.read_all()], harapan)
        self.assertEqual(
            [j.get_nama_jenis() for j in self.repo_jenis.read_by_names(
                ["Mangga", "Durian", "alpukat"])], harapan)
        self.assertEqual(
            [k.get_nama_keterangan() for k in self.repo_keterangan.read_all()], harapan)
        self.assertEqual(
            [k.get_nama_keterangan() for k in self.repo_keterangan.read_by_names(
                ["Mangga", "Durian", "alpukat"])], harapan)

    def test_urutan_pohon_berdasarkan_nomor(self):
        for nomor in (10, 2, 7):
            self.repo_pohon.create(Pohon(nomor))
        self.assertEqual([p.get_nomor_pohon() for p in self.repo_pohon.read_all()], [2, 7, 10])
        self.assertEqual(
            [p.get_nomor_pohon() for p in self.repo_pohon.read_by_numbers([10, 2])],
            [2, 10])

    def test_urutan_varietas_berdasarkan_jenis_lalu_nama(self):
        mangga, durian = JenisTanaman("Mangga"), JenisTanaman("Durian")
        self.repo_jenis.create(mangga)
        self.repo_jenis.create(durian)
        for nama, jenis in (("Arumanis", mangga), ("Musang King", durian),
                            ("Lokal", mangga), ("D24", durian), ("Lokal", durian)):
            self.repo_varietas.create(Varietas(nama, jenis))

        def urutan(daftar):
            return [(v.get_jenis().get_nama_jenis(), v.get_nama_varietas()) for v in daftar]

        self.assertEqual(urutan(self.repo_varietas.read_all()), [
            ("Durian", "D24"), ("Durian", "Lokal"), ("Durian", "Musang King"),
            ("Mangga", "Arumanis"), ("Mangga", "Lokal")])
        self.assertEqual(
            urutan(self.repo_varietas.read_by_names(["Lokal", "Arumanis"])),
            [("Durian", "Lokal"), ("Mangga", "Arumanis"), ("Mangga", "Lokal")])

    def test_urutan_buah_berdasarkan_tanggal_lalu_nomor_pohon(self):
        self.simpan_induk()
        pohon_2 = Pohon(2)
        self.repo_pohon.create(pohon_2)
        for tanggal, pohon in (("2026-01-16", self.pohon), ("2026-01-15", self.pohon),
                               ("2026-01-16", pohon_2), ("2026-01-15", pohon_2)):
            self.repo_buah.create(self.buah_baru(tanggal_panen=tanggal, pohon=pohon))

        def urutan(daftar):
            return [(b.get_tanggal_panen(), b.get_pohon().get_nomor_pohon()) for b in daftar]

        semua = [("2026-01-15", 2), ("2026-01-15", 7), ("2026-01-16", 2), ("2026-01-16", 7)]
        self.assertEqual(urutan(self.repo_buah.read_all()), semua)
        self.assertEqual(
            urutan(self.repo_buah.read_by_harvest_dates(
                ["2026-01-16", "2026-01-15"])), semua)
        self.assertEqual(
            urutan(self.repo_buah.read_by_harvest_date("2026-01-16")),
            [("2026-01-16", 2), ("2026-01-16", 7)])

    def test_urutan_periode_berdasarkan_tanggal_mulai(self):
        self.repo_periode.create(PeriodePanen("Kedua", "2026-04-01", "2026-05-31"))
        self.repo_periode.create(PeriodePanen("Pertama", "2026-01-01", "2026-03-31"))
        self.repo_periode.create(PeriodePanen("Ketiga", "2026-06-01", None))
        self.assertEqual([p.get_nama() for p in self.repo_periode.read_all()],
                         ["Pertama", "Kedua", "Ketiga"])

    # ---- hapus ----

    def test_delete(self):
        self.simpan_induk()
        buah = self.buah_baru()
        self.repo_buah.create(buah)
        periode = PeriodePanen("A", "2026-01-01", None)
        self.repo_periode.create(periode)

        # urutan dari anak ke induk agar foreign key tidak menolak
        kasus = [
            (self.repo_buah, buah.get_id_buah()),
            (self.repo_varietas, self.varietas.get_id_varietas()),
            (self.repo_jenis, self.jenis.get_id_jenis()),
            (self.repo_pohon, self.pohon.get_id_pohon()),
            (self.repo_keterangan, self.baik.get_id_keterangan()),
            (self.repo_periode, periode.get_id_periode()),
        ]
        for repo, id_objek in kasus:
            repo.delete(id_objek)
            self.assertIsNone(repo.read(id_objek), type(repo).__name__)

    def test_delete_hanya_menghapus_id_yang_diminta(self):
        pohon_8 = Pohon(8)
        self.repo_pohon.create(self.pohon)
        self.repo_pohon.create(pohon_8)
        self.repo_pohon.delete(self.pohon.get_id_pohon())
        self.assertEqual(self.id_dari(self.repo_pohon.read_all(), "get_id_pohon"),
                         {pohon_8.get_id_pohon()})

    def test_delete_id_yang_tidak_ada_tidak_error(self):
        self.repo_pohon.create(self.pohon)
        self.repo_pohon.delete("tidak-ada")
        self.assertEqual(len(self.repo_pohon.read_all()), 1)

    def test_delete_induk_yang_masih_dipakai_ditolak(self):
        self.simpan_induk()
        self.repo_buah.create(self.buah_baru())
        kasus = [
            (self.repo_pohon, self.pohon.get_id_pohon()),
            (self.repo_varietas, self.varietas.get_id_varietas()),
            (self.repo_keterangan, self.baik.get_id_keterangan()),
            (self.repo_jenis, self.jenis.get_id_jenis()),
        ]
        for repo, id_objek in kasus:
            with self.assertRaises(sqlite3.IntegrityError, msg=type(repo).__name__):
                repo.delete(id_objek)
            self.assertIsNotNone(repo.read(id_objek), type(repo).__name__)

    # ---- perbarui ----

    def test_update_jenis_tanaman(self):
        self.repo_jenis.create(self.jenis)
        self.jenis.set_nama_jenis("Durian Lokal")
        self.jenis.set_deskripsi("Baru")
        self.repo_jenis.update(self.jenis)
        hasil = self.repo_jenis.read(self.jenis.get_id_jenis())
        self.assertEqual(hasil.get_nama_jenis(), "Durian Lokal")
        self.assertEqual(hasil.get_deskripsi(), "Baru")

    def test_update_varietas_termasuk_pindah_jenis(self):
        self.simpan_induk()
        mangga = JenisTanaman("Mangga")
        self.repo_jenis.create(mangga)
        self.varietas.set_nama_varietas("Arumanis")
        self.varietas.set_jenis(mangga)
        self.varietas.set_deskripsi("Harum")
        self.repo_varietas.update(self.varietas)
        hasil = self.repo_varietas.read(self.varietas.get_id_varietas())
        self.assertEqual(hasil.get_nama_varietas(), "Arumanis")
        self.assertEqual(hasil.get_jenis().get_id_jenis(), mangga.get_id_jenis())
        self.assertEqual(hasil.get_deskripsi(), "Harum")

    def test_update_pohon(self):
        self.repo_pohon.create(self.pohon)
        self.pohon.set_nomor_pohon(10)
        self.repo_pohon.update(self.pohon)
        self.assertEqual(self.repo_pohon.read(self.pohon.get_id_pohon()).get_nomor_pohon(), 10)

    def test_update_keterangan_buah(self):
        self.repo_keterangan.create(self.baik)
        self.baik.set_nama_keterangan("Bagus")
        self.baik.set_deskripsi("Mulus")
        self.repo_keterangan.update(self.baik)
        hasil = self.repo_keterangan.read(self.baik.get_id_keterangan())
        self.assertEqual(hasil.get_nama_keterangan(), "Bagus")
        self.assertEqual(hasil.get_deskripsi(), "Mulus")

    def test_update_buah(self):
        self.simpan_induk()
        buah = self.buah_baru()
        self.repo_buah.create(buah)
        pohon_2, d24, busuk = Pohon(8), Varietas("D24", self.jenis), KeteranganBuah("Busuk")
        self.repo_pohon.create(pohon_2)
        self.repo_varietas.create(d24)
        self.repo_keterangan.create(busuk)

        buah.set_pohon(pohon_2)
        buah.set_varietas(d24)
        buah.set_keterangan(busuk)
        buah.set_bobot(2.5)
        buah.set_tanggal_panen("2026-02-01")
        self.repo_buah.update(buah)

        hasil = self.repo_buah.read(buah.get_id_buah())
        self.assertEqual(hasil.get_pohon().get_id_pohon(), pohon_2.get_id_pohon())
        self.assertEqual(hasil.get_varietas().get_id_varietas(), d24.get_id_varietas())
        self.assertEqual(hasil.get_keterangan().get_id_keterangan(), busuk.get_id_keterangan())
        self.assertEqual(hasil.get_bobot(), 2.5)
        self.assertEqual(hasil.get_tanggal_panen(), "2026-02-01")

    def test_update_periode_panen(self):
        periode = PeriodePanen("A", "2026-01-01", None)
        self.repo_periode.create(periode)
        periode.set_nama("Raya")
        periode.set_tanggal_selesai("2026-03-31")
        periode.set_deskripsi("Ditutup")
        self.repo_periode.update(periode)
        hasil = self.repo_periode.read(periode.get_id_periode())
        self.assertEqual(hasil.get_nama(), "Raya")
        self.assertEqual(hasil.get_tanggal_selesai(), "2026-03-31")
        self.assertEqual(hasil.get_deskripsi(), "Ditutup")
        self.assertFalse(hasil.is_active())

    def test_update_hanya_mengubah_id_yang_diminta(self):
        pohon_8 = Pohon(8)
        self.repo_pohon.create(self.pohon)
        self.repo_pohon.create(pohon_8)
        self.pohon.set_nomor_pohon(10)
        self.repo_pohon.update(self.pohon)
        self.assertEqual(self.repo_pohon.read(pohon_8.get_id_pohon()).get_nomor_pohon(), 8)

    def test_update_tetap_mengikuti_aturan_skema(self):
        self.simpan_induk()
        buah = self.buah_baru()
        self.repo_buah.create(buah)
        pohon_8 = Pohon(8)
        self.repo_pohon.create(pohon_8)

        pohon_8.set_nomor_pohon(7)
        with self.assertRaises(sqlite3.IntegrityError, msg="nomor pohon ganda"):
            self.repo_pohon.update(pohon_8)

        buah.set_bobot(0)
        with self.assertRaises(sqlite3.IntegrityError, msg="bobot nol"):
            self.repo_buah.update(buah)

        buah.set_bobot(1.0)
        buah.set_pohon(Pohon(99))
        with self.assertRaises(sqlite3.IntegrityError, msg="pohon belum disimpan"):
            self.repo_buah.update(buah)

        self.repo_periode.create(PeriodePanen("A", "2026-01-01", "2026-03-31"))
        b = PeriodePanen("B", "2026-06-01", "2026-08-31")
        self.repo_periode.create(b)
        b.set_tanggal_mulai("2026-03-01")
        with self.assertRaises(sqlite3.IntegrityError, msg="periode tumpang tindih"):
            self.repo_periode.update(b)


if __name__ == "__main__":
    unittest.main()
