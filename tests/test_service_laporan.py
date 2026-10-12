import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pencatatan_kebun.db.koneksi import buka_koneksi
from pencatatan_kebun.models import JenisTanaman
from pencatatan_kebun.services.exception import DataTidakDitemukanException
from pencatatan_kebun.services.laporan import LaporanService
from pencatatan_kebun.services.master import MasterService
from pencatatan_kebun.services.panen import PanenService
from pencatatan_kebun.services.periode import PeriodeService
from pencatatan_kebun.services.stok import StokService


class DasarLaporan(unittest.TestCase):
    """Persiapan bersama; tidak berisi tes.

    Durian di periode Raya 2025:
        Bawor 1: stok 10, panen Baik 2.0, Baik 3.0, Gugur 1.0
        Bawor 2: stok 5,  panen Baik 2.5
        Montong 1: stok 4, panen Rusak 4.0
        Musangking 1: stok 2, belum panen
    Alpukat: Kendil 1 stok 3, panen Baik 0.5. Mangga tanpa data.
    """

    def setUp(self):
        self.conn = buka_koneksi(":memory:")
        self.addCleanup(self.conn.close)
        self.master = MasterService(self.conn)
        self.panen = PanenService(self.conn)
        self.stok = StokService(self.conn)
        self.periode_service = PeriodeService(self.conn)
        self.service = LaporanService(self.conn)

        self.durian = self.master.tambah_jenis("Durian")
        self.alpukat = self.master.tambah_jenis("Alpukat")
        self.mangga = self.master.tambah_jenis("Mangga")
        bawor = self.master.tambah_varietas(self.durian, "Bawor")
        montong = self.master.tambah_varietas(self.durian, "Montong")
        musangking = self.master.tambah_varietas(self.durian, "Musangking")
        kendil = self.master.tambah_varietas(self.alpukat, "Kendil")
        self.master.tambah_varietas(self.mangga, "Arumanis")
        self.bawor_1 = self.master.tambah_pohon(bawor, 1)
        self.bawor_2 = self.master.tambah_pohon(bawor, 2)
        self.bawor_3 = self.master.tambah_pohon(bawor, 3)
        montong_1 = self.master.tambah_pohon(montong, 1)
        musangking_1 = self.master.tambah_pohon(musangking, 1)
        kendil_1 = self.master.tambah_pohon(kendil, 1)
        self.baik = self.master.tambah_keterangan("Baik")
        self.rusak = self.master.tambah_keterangan("Rusak")
        self.gugur = self.master.tambah_keterangan("Gugur")

        self.periode = self.periode_service.buka_periode("Raya 2025", "2025-01-01", "2025-03-31")
        for pohon, jumlah in ((self.bawor_1, 10), (self.bawor_2, 5), (montong_1, 4),
                              (musangking_1, 2), (kendil_1, 3)):
            self.stok.catat_stok(pohon, self.periode, jumlah, "2025-01-02")

        for pohon, keterangan, bobot, tanggal in (
                (self.bawor_1, self.baik, 2.0, "2025-01-01"),
                (self.bawor_1, self.baik, 3.0, "2025-03-31"),
                (self.bawor_1, self.gugur, 1.0, "2025-02-01"),
                (self.bawor_2, self.baik, 2.5, "2025-02-01"),
                (montong_1, self.rusak, 4.0, "2025-02-10"),
                (kendil_1, self.baik, 0.5, "2025-02-10"),
                (self.bawor_1, self.baik, 9.0, "2024-12-31"),
                (self.bawor_1, self.baik, 9.0, "2025-04-01")):
            self.panen.catat_buah(pohon, keterangan, bobot, tanggal)

    def ringkasan_durian(self):
        return self.service.ringkasan_jenis(self.periode.get_id_periode(), self.durian)


class TestRingkasanJenis(DasarLaporan):
    def test_ringkasan_total_jenis(self):
        r = self.ringkasan_durian()["ringkasan"]
        self.assertEqual((r["jumlah_stok"], r["jumlah_panen"], r["sisa"]), (21, 5, 16))
        self.assertAlmostEqual(r["total_bobot"], 12.5)
        self.assertAlmostEqual(r["rata_rata_bobot"], 2.5)

    def test_persentase_keterangan_jenis_dari_seluruh_panen(self):
        k = self.ringkasan_durian()["ringkasan"]["per_keterangan"]
        self.assertEqual(list(k), ["Baik", "Gugur", "Rusak"])
        self.assertEqual(k["Baik"]["jumlah_buah"], 3)
        self.assertAlmostEqual(k["Baik"]["persentase"], 60.0)
        self.assertAlmostEqual(k["Baik"]["total_bobot"], 7.5)
        self.assertAlmostEqual(k["Gugur"]["persentase"], 20.0)
        self.assertAlmostEqual(k["Rusak"]["persentase"], 20.0)
        self.assertAlmostEqual(sum(x["persentase"] for x in k.values()), 100.0)

    def test_per_varietas(self):
        per_varietas = self.ringkasan_durian()["per_varietas"]
        self.assertEqual(list(per_varietas), ["Bawor", "Montong", "Musangking"])
        bawor = per_varietas["Bawor"]
        self.assertEqual(bawor["varietas"].get_nama_varietas(), "Bawor")
        self.assertEqual((bawor["jumlah_stok"], bawor["jumlah_panen"], bawor["sisa"]), (15, 4, 11))
        self.assertAlmostEqual(bawor["total_bobot"], 8.5)
        self.assertAlmostEqual(bawor["rata_rata_bobot"], 2.125)
        self.assertEqual((bawor["bobot_min"], bawor["bobot_max"]), (1.0, 3.0))

    def test_persentase_keterangan_varietas_dari_panen_varietas_itu(self):
        per_varietas = self.ringkasan_durian()["per_varietas"]
        bawor = per_varietas["Bawor"]["per_keterangan"]
        self.assertAlmostEqual(bawor["Baik"]["persentase"], 75.0)
        self.assertAlmostEqual(bawor["Gugur"]["persentase"], 25.0)
        self.assertEqual(bawor["Rusak"], {"jumlah_buah": 0, "persentase": 0.0, "total_bobot": 0.0})
        self.assertAlmostEqual(per_varietas["Montong"]["per_keterangan"]["Rusak"]["persentase"], 100.0)

    def test_semua_varietas_punya_keterangan_yang_sama(self):
        per_varietas = self.ringkasan_durian()["per_varietas"]
        for nama, v in per_varietas.items():
            self.assertEqual(list(v["per_keterangan"]), ["Baik", "Gugur", "Rusak"], nama)

    def test_varietas_belum_panen_tetap_muncul_dengan_nol(self):
        musangking = self.ringkasan_durian()["per_varietas"]["Musangking"]
        self.assertEqual((musangking["jumlah_stok"], musangking["jumlah_panen"], musangking["sisa"]),
                         (2, 0, 2))
        self.assertEqual(musangking["rata_rata_bobot"], 0.0)
        self.assertIsNone(musangking["bobot_min"])
        self.assertIsNone(musangking["bobot_max"])
        self.assertTrue(all(k["persentase"] == 0.0 for k in musangking["per_keterangan"].values()))

    def test_panen_pohon_tanpa_stok_ikut_mengurangi_sisa(self):
        self.panen.catat_buah(self.bawor_3, self.baik, 1.0, "2025-02-01")
        bawor = self.ringkasan_durian()["per_varietas"]["Bawor"]
        self.assertEqual((bawor["jumlah_stok"], bawor["jumlah_panen"], bawor["sisa"]), (15, 5, 10))

    def test_jenis_lain_tidak_ikut(self):
        alpukat = self.service.ringkasan_jenis(self.periode.get_id_periode(), self.alpukat)
        self.assertEqual(list(alpukat["per_varietas"]), ["Kendil"])
        self.assertEqual(alpukat["ringkasan"]["jumlah_panen"], 1)
        self.assertEqual(list(alpukat["ringkasan"]["per_keterangan"]), ["Baik"])

    def test_jenis_tanpa_data(self):
        hasil = self.service.ringkasan_jenis(self.periode.get_id_periode(), self.mangga)
        self.assertEqual(hasil["per_varietas"], {})
        self.assertEqual(hasil["ringkasan"], {
            "jumlah_stok": 0, "jumlah_panen": 0, "sisa": 0,
            "total_bobot": 0.0, "rata_rata_bobot": 0.0, "per_keterangan": {}})

    def test_periode_aktif_dihitung_sampai_hari_ini(self):
        aktif = self.periode_service.buka_periode("Berjalan", "2025-06-01")
        self.stok.catat_stok(self.bawor_1, aktif, 5, "2025-06-01")
        self.panen.catat_buah(self.bawor_1, self.baik, 2.0, "2025-06-10")
        self.panen.catat_buah(self.bawor_1, self.baik, 2.0, date.today().isoformat())
        hasil = self.service.ringkasan_jenis(aktif.get_id_periode(), self.durian)
        self.assertEqual(hasil["ringkasan"]["jumlah_panen"], 2)
        self.assertEqual(hasil["ringkasan"]["sisa"], 3)

    def test_periode_atau_jenis_tidak_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException) as cm:
            self.service.ringkasan_jenis("tidak-ada", self.durian)
        self.assertEqual(cm.exception.kolom, "id_periode")
        with self.assertRaises(DataTidakDitemukanException) as cm:
            self.service.ringkasan_jenis(self.periode.get_id_periode(), JenisTanaman("Rambutan"))
        self.assertEqual(cm.exception.kolom, "id_jenis")


class TestRingkasanPerPohon(DasarLaporan):
    def test_per_pohon(self):
        self.panen.catat_buah(self.bawor_3, self.baik, 1.0, "2025-02-01")
        hasil = self.service.ringkasan_per_pohon(self.periode.get_id_periode(), self.durian)
        self.assertEqual(
            [(p["nama_varietas"], p["nomor_pohon"], p["jumlah_stok"], p["jumlah_panen"], p["sisa"])
             for p in hasil],
            [("Bawor", 1, 10, 3, 7), ("Bawor", 2, 5, 1, 4), ("Bawor", 3, 0, 1, -1),
             ("Montong", 1, 4, 1, 3), ("Musangking", 1, 2, 0, 2)])
        self.assertAlmostEqual(hasil[0]["total_bobot"], 6.0)
        self.assertEqual(hasil[-1]["total_bobot"], 0.0)

    def test_per_pohon_jenis_tanpa_data(self):
        self.assertEqual(
            self.service.ringkasan_per_pohon(self.periode.get_id_periode(), self.mangga), [])

    def test_per_pohon_periode_tidak_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException):
            self.service.ringkasan_per_pohon("tidak-ada", self.durian)


class TestDashboard(DasarLaporan):
    def test_hanya_jenis_yang_punya_data_urut_nama(self):
        hasil = self.service.dashboard(self.periode.get_id_periode())
        self.assertEqual(hasil["periode"].get_nama(), "Raya 2025")
        self.assertEqual(list(hasil["per_jenis"]), ["Alpukat", "Durian"])
        durian = hasil["per_jenis"]["Durian"]
        self.assertEqual(durian["jenis"].get_id_jenis(), self.durian.get_id_jenis())
        self.assertEqual(durian["ringkasan"], self.ringkasan_durian()["ringkasan"])
        self.assertEqual(list(durian["per_varietas"]), ["Bawor", "Montong", "Musangking"])

    def test_periode_tanpa_data(self):
        kosong = self.periode_service.buka_periode("Kosong", "2025-06-01", "2025-06-30")
        self.assertEqual(self.service.dashboard(kosong.get_id_periode())["per_jenis"], {})

    def test_periode_tidak_ada_ditolak(self):
        with self.assertRaises(DataTidakDitemukanException):
            self.service.dashboard("tidak-ada")


if __name__ == "__main__":
    unittest.main()
