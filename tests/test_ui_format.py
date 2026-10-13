import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pencatatan_kebun.ui.format import (
    format_kg,
    format_persen,
    kalimat,
    tanggal_ke_tampil,
    teks_ke_bobot,
    teks_ke_int,
)


class TestTeksKeBobot(unittest.TestCase):
    def test_titik_dan_koma_desimal(self):
        self.assertEqual(teks_ke_bobot("2.5"), 2.5)
        self.assertEqual(teks_ke_bobot("2,5"), 2.5)
        self.assertEqual(teks_ke_bobot(" 3 "), 3.0)

    def test_kosong_atau_bukan_angka_jadi_none(self):
        for teks in (None, "", "   ", "abc", "1,2,3", "nan", "inf"):
            with self.subTest(teks=teks):
                self.assertIsNone(teks_ke_bobot(teks))

    def test_nol_dan_negatif_diteruskan_ke_service(self):
        self.assertEqual(teks_ke_bobot("0"), 0.0)
        self.assertEqual(teks_ke_bobot("-1,5"), -1.5)


class TestTeksKeInt(unittest.TestCase):
    def test_bilangan_bulat(self):
        self.assertEqual(teks_ke_int("7"), 7)
        self.assertEqual(teks_ke_int(" 12 "), 12)
        self.assertEqual(teks_ke_int("-3"), -3)

    def test_bukan_bilangan_bulat_jadi_none(self):
        for teks in (None, "", "abc", "7,5", "7.0", "1_000", "1e3"):
            with self.subTest(teks=teks):
                self.assertIsNone(teks_ke_int(teks))


class TestTanggal(unittest.TestCase):
    def test_db_ke_tampil(self):
        self.assertEqual(tanggal_ke_tampil("2026-10-13"), "13-10-2026")
        self.assertEqual(tanggal_ke_tampil(None), "")
        self.assertEqual(tanggal_ke_tampil("salah"), "salah")


class TestFormatAngka(unittest.TestCase):
    def test_format_kg(self):
        self.assertEqual(format_kg(2.5), "2,50")
        self.assertEqual(format_kg(1234.5, desimal=1), "1.234,5")
        self.assertEqual(format_kg(None), "-")

    def test_format_persen(self):
        self.assertEqual(format_persen(12.345), "12,3%")
        self.assertEqual(format_persen(100), "100,0%")
        self.assertEqual(format_persen(None), "-")


class TestKalimat(unittest.TestCase):
    def test_hanya_huruf_pertama_diubah(self):
        self.assertEqual(kalimat("periode Raya 2026"), "Periode Raya 2026")
        self.assertEqual(kalimat(""), "")


if __name__ == "__main__":
    unittest.main()
