import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pencatatan_kebun.ui.kalender import (
    boleh_dipilih,
    bulan_bisa_dibuka,
    geser_bulan,
    minggu_bulan,
    sehari_setelah,
)


class TestMingguBulan(unittest.TestCase):
    def test_minggu_mulai_senin_dan_hari_luar_bulan_kosong(self):
        # 1 Oktober 2026 jatuh pada hari Kamis.
        minggu = minggu_bulan(2026, 10)
        self.assertEqual(minggu[0], [None, None, None, date(2026, 10, 1), date(2026, 10, 2),
                                     date(2026, 10, 3), date(2026, 10, 4)])
        self.assertEqual(minggu[-1][-1 - minggu[-1][::-1].index(date(2026, 10, 31))],
                         date(2026, 10, 31))
        semua = [t for m in minggu for t in m if t is not None]
        self.assertEqual(len(semua), 31)
        self.assertTrue(all(len(m) == 7 for m in minggu))

    def test_februari_kabisat(self):
        semua = [t for m in minggu_bulan(2028, 2) for t in m if t is not None]
        self.assertEqual(semua[-1], date(2028, 2, 29))


class TestBatas(unittest.TestCase):
    def test_tanpa_batas_semua_boleh(self):
        self.assertTrue(boleh_dipilih(date(1990, 1, 1), None, None))

    def test_batas_ikut_dihitung(self):
        awal, akhir = date(2026, 3, 1), date(2026, 3, 31)
        self.assertTrue(boleh_dipilih(awal, awal, akhir))
        self.assertTrue(boleh_dipilih(akhir, awal, akhir))
        self.assertFalse(boleh_dipilih(date(2026, 2, 28), awal, akhir))
        self.assertFalse(boleh_dipilih(date(2026, 4, 1), awal, akhir))

    def test_bulan_bisa_dibuka(self):
        hari_ini = date(2026, 10, 13)
        self.assertTrue(bulan_bisa_dibuka(2026, 10, None, hari_ini))
        self.assertFalse(bulan_bisa_dibuka(2026, 11, None, hari_ini))
        self.assertTrue(bulan_bisa_dibuka(2026, 3, date(2026, 3, 31), None))
        self.assertFalse(bulan_bisa_dibuka(2026, 2, date(2026, 3, 1), None))


class TestGeser(unittest.TestCase):
    def test_geser_melewati_tahun(self):
        self.assertEqual(geser_bulan(2026, 12, 1), (2027, 1))
        self.assertEqual(geser_bulan(2026, 1, -1), (2025, 12))
        self.assertEqual(geser_bulan(2026, 5, -12), (2025, 5))

    def test_sehari_setelah(self):
        self.assertEqual(sehari_setelah(date(2026, 2, 28)), date(2026, 3, 1))
        self.assertIsNone(sehari_setelah(None))


if __name__ == "__main__":
    unittest.main()
