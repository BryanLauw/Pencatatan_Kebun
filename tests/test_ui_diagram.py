import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pencatatan_kebun.ui.diagram import (
    LABEL_LAINNYA,
    PALET,
    WARNA_BAIK,
    WARNA_GUGUR,
    WARNA_LAINNYA,
    WARNA_RUSAK,
    kelompokkan,
    warna_kategori,
    warna_keterangan,
)


class TestKelompokkan(unittest.TestCase):
    def test_nilai_nol_dibuang(self):
        self.assertEqual(kelompokkan([("Baik", 5), ("Rusak", 0)]), [("Baik", 5)])

    def test_tidak_lebih_dari_maks_tetap_utuh(self):
        data = [(f"V{i}", i) for i in range(1, 7)]
        self.assertEqual(kelompokkan(data, maks=6), data)

    def test_terkecil_digabung_jadi_lainnya_urutan_tetap(self):
        data = [("A", 1), ("B", 10), ("C", 2), ("D", 8), ("E", 9)]
        self.assertEqual(kelompokkan(data, maks=3),
                         [("B", 10), ("E", 9), (LABEL_LAINNYA, 11)])


class TestWarnaKategori(unittest.TestCase):
    def test_warna_mengikuti_urutan_kategori(self):
        warna = warna_kategori(["Baik", "Gugur", "Rusak"])
        self.assertEqual(warna, {"Baik": PALET[0], "Gugur": PALET[1], "Rusak": PALET[2]})

    def test_kategori_setelah_palet_habis_abu_abu(self):
        warna = warna_kategori([f"K{i}" for i in range(len(PALET) + 1)])
        self.assertEqual(warna[f"K{len(PALET)}"], WARNA_LAINNYA)


class TestWarnaKeterangan(unittest.TestCase):
    def test_nama_bermakna_pakai_warna_makna(self):
        warna = warna_keterangan(["Baik", "Gugur", "Rusak"])
        self.assertEqual(warna, {"Baik": WARNA_BAIK, "Gugur": WARNA_GUGUR, "Rusak": WARNA_RUSAK})

    def test_huruf_besar_kecil_dan_spasi_diabaikan(self):
        self.assertEqual(warna_keterangan([" BUSUK "])[" BUSUK "], WARNA_RUSAK)

    def test_nama_lain_pakai_palet_berurutan(self):
        warna = warna_keterangan(["Kecil", "Baik", "Retak"])
        self.assertEqual(warna, {"Kecil": PALET[0], "Baik": WARNA_BAIK, "Retak": PALET[1]})

    def test_palet_tidak_memakai_warna_makna(self):
        self.assertFalse({WARNA_BAIK, WARNA_GUGUR, WARNA_RUSAK} & set(PALET))


if __name__ == "__main__":
    unittest.main()
