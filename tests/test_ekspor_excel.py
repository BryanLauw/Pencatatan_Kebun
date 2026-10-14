import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from openpyxl import load_workbook

from pencatatan_kebun.db.koneksi import buka_koneksi
from pencatatan_kebun.ekspor.excel import (
    SHEET_BUAH,
    SHEET_RINGKASAN,
    kumpulkan_data,
    nama_file_bawaan,
    nama_sheet_aman,
    tulis_excel,
)
from pencatatan_kebun.models import PeriodePanen
from pencatatan_kebun.services.laporan import LaporanService
from pencatatan_kebun.services.master import MasterService
from pencatatan_kebun.services.panen import PanenService
from pencatatan_kebun.services.periode import PeriodeService
from pencatatan_kebun.services.stok import StokService


def _cari_libreoffice() -> str | None:
    for lokasi in (shutil.which("soffice"), r"C:\Program Files\LibreOffice\program\soffice.exe"):
        if lokasi and Path(lokasi).exists():
            return lokasi
    return None


class DasarEkspor(unittest.TestCase):
    """Dua jenis; Durian punya pohon tanpa stok, pohon tanpa panen, dan sisa negatif."""

    def setUp(self):
        self.conn = buka_koneksi(":memory:")
        self.addCleanup(self.conn.close)
        self.master = MasterService(self.conn)
        self.stok = StokService(self.conn)
        self.panen = PanenService(self.conn)
        self.laporan = LaporanService(self.conn)
        m = self.master
        durian, alpukat = m.tambah_jenis("Durian"), m.tambah_jenis("Alpukat")
        m.tambah_jenis("Mangga")  # tanpa data: tidak dapat sheet
        baik, gugur, rusak = (m.tambah_keterangan(n) for n in ("Baik", "Gugur", "Rusak"))
        self.periode = PeriodeService(self.conn).buka_periode("Raya 2026", "2026-09-01")
        bawor, mk = m.tambah_varietas(durian, "Bawor"), m.tambah_varietas(durian, "Musang King")
        aligator = m.tambah_varietas(alpukat, "Aligator")
        b1, b2 = m.tambah_pohon(bawor, 1), m.tambah_pohon(bawor, 2)
        m.tambah_pohon(bawor, 3)  # tanpa stok dan panen
        mk1, a1 = m.tambah_pohon(mk, 1), m.tambah_pohon(aligator, 1)
        self.stok.catat_stok(b1, self.periode, 11, "2026-09-03")
        self.stok.catat_stok(b2, self.periode, 2, "2026-09-03")
        self.stok.catat_stok(a1, self.periode, 5, "2026-09-04")
        for pohon, ket, bobot, tanggal in [
                (b1, baik, 2.4, "2026-09-08"), (b1, baik, 2.5, "2026-09-08"),
                (b1, gugur, 2.0, "2026-09-14"), (b2, baik, 4.7, "2026-09-09"),
                (b2, rusak, 4.6, "2026-09-14"), (b2, baik, 3.0, "2026-09-14"),
                (mk1, baik, 3.5, "2026-09-20"), (a1, baik, 0.4, "2026-09-10")]:
            self.panen.catat_buah(pohon, ket, bobot, tanggal)

    def data(self):
        return kumpulkan_data(self.master, self.stok, self.panen, self.laporan, self.periode)

    def tulis(self) -> Path:
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        lokasi = Path(folder) / "laporan.xlsx"
        tulis_excel(self.data(), lokasi)
        return lokasi


class TestKumpulkanData(DasarEkspor):
    def test_hanya_jenis_dengan_data_urut_nama(self):
        self.assertEqual([j["nama"] for j in self.data()["jenis"]], ["Alpukat", "Durian"])

    def test_semua_pohon_jenis_tampil_dengan_angka_per_tanggal(self):
        durian = self.data()["jenis"][1]
        self.assertEqual(durian["tanggal"], [date(2026, 9, 8), date(2026, 9, 9),
                                             date(2026, 9, 14), date(2026, 9, 20)])
        self.assertEqual(durian["keterangan"], ["Baik", "Gugur", "Rusak"])
        pohon = {(p["varietas"], p["nomor"]): p for p in durian["pohon"]}
        self.assertEqual(list(pohon), [("Bawor", 1), ("Bawor", 2), ("Bawor", 3), ("Musang King", 1)])
        b1 = pohon[("Bawor", 1)]
        self.assertEqual((b1["stok"], b1["tgl_hitung"], b1["panen"]), (11, date(2026, 9, 3), 3))
        self.assertEqual(b1["per_tanggal"], {date(2026, 9, 8): 2, date(2026, 9, 14): 1})
        self.assertEqual(b1["per_keterangan"], {"Baik": 2, "Gugur": 1})
        self.assertAlmostEqual(b1["kg"], 6.9)
        self.assertIsNone(pohon[("Bawor", 3)]["stok"])
        self.assertIsNone(pohon[("Musang King", 1)]["stok"])

    def test_angka_sama_dengan_laporan_service(self):
        for jenis in self.data()["jenis"]:
            r = jenis["ringkasan"]["ringkasan"]
            self.assertEqual(sum(p["stok"] or 0 for p in jenis["pohon"]), r["jumlah_stok"])
            self.assertEqual(sum(p["panen"] for p in jenis["pohon"]), r["jumlah_panen"])
            self.assertAlmostEqual(sum(p["kg"] for p in jenis["pohon"]), r["total_bobot"])

    def test_catatan_buah_urut_tanggal(self):
        buah = self.data()["buah"]
        self.assertEqual(len(buah), 8)
        self.assertEqual([b["tanggal"] for b in buah], sorted(b["tanggal"] for b in buah))


class TestNama(unittest.TestCase):
    def test_nama_file(self):
        periode = PeriodePanen("Raya: 2026/27", "2026-09-01")
        self.assertEqual(nama_file_bawaan(periode, date(2026, 10, 14)),
                         "Laporan Panen Raya 2026 27 14-10-2026.xlsx")

    def test_nama_sheet_aman_dan_unik(self):
        terpakai = {"ringkasan"}
        self.assertEqual(nama_sheet_aman("Ringkasan", terpakai), "Ringkasan (2)")
        self.assertEqual(nama_sheet_aman("A/B?", terpakai), "A B")
        panjang = nama_sheet_aman("x" * 40, terpakai)
        self.assertEqual(len(panjang), 31)
        self.assertEqual(len(nama_sheet_aman("x" * 40, terpakai)), 31)


class TestTulisExcel(DasarEkspor):
    def test_urutan_sheet(self):
        wb = load_workbook(self.tulis())
        self.assertEqual(wb.sheetnames, [SHEET_RINGKASAN, "Alpukat", "Durian", SHEET_BUAH])

    def test_sheet_jenis_angka_isian_dan_rumus(self):
        ws = load_workbook(self.tulis())["Durian"]
        # Header tanggal di baris 4 (F-I), lalu Panen di J.
        self.assertEqual([ws.cell(4, k).value.date() for k in range(6, 10)],
                         [date(2026, 9, 8), date(2026, 9, 9), date(2026, 9, 14), date(2026, 9, 20)])
        self.assertEqual(ws["J4"].value, "Panen")
        # Bawor 1 di baris 5: angka isian.
        self.assertEqual([ws[f"{k}5"].value for k in "BCE"], ["Bawor", 1, 11])
        self.assertEqual((ws["F5"].value, ws["G5"].value, ws["H5"].value), (2, None, 1))
        self.assertAlmostEqual(ws["L5"].value, 6.9)
        # Hasil hitungan berupa rumus.
        self.assertEqual(ws["J5"].value, "=SUM(F5:I5)")
        self.assertEqual(ws["K5"].value, "=E5-J5")
        self.assertEqual(ws["M5"].value, '=IF(J5=0,"",L5/J5)')
        # Baris Total setelah 4 pohon.
        self.assertEqual(ws["B9"].value, "Total")
        self.assertEqual(ws["E9"].value, "=SUM(E5:E8)")
        self.assertEqual(ws["J9"].value, "=SUM(J5:J8)")

    def test_ringkasan_varietas_pakai_sumif(self):
        ws = load_workbook(self.tulis())["Durian"]
        baris = next(r for r in range(10, ws.max_row + 1) if ws[f"B{r}"].value == "Bawor")
        self.assertEqual(ws[f"C{baris}"].value, f"=SUMIF($B$5:$B$8,$B{baris},E$5:E$8)")
        self.assertIn("SUMIFS('Catatan buah'!$F:$F", ws[f"L{baris}"].value)
        self.assertEqual(ws[f"H{baris}"].value, 2.0)   # min kg Bawor (angka isian)

    def test_ringkasan_merujuk_sheet_jenis(self):
        ws = load_workbook(self.tulis())[SHEET_RINGKASAN]
        self.assertEqual(ws["A7"].value, "Durian")
        self.assertEqual(ws["D7"].value, "='Durian'!J9")

    def test_catatan_buah(self):
        ws = load_workbook(self.tulis())[SHEET_BUAH]
        self.assertEqual(ws.max_row, 9)  # header + 8 buah
        self.assertEqual([c.value for c in ws[2]][1:], ["Durian", "Bawor", 1, "Baik", 2.4])


@unittest.skipUnless(_cari_libreoffice(), "LibreOffice tidak terpasang")
class TestHasilRumus(DasarEkspor):
    """Hitung ulang rumus dengan LibreOffice, lalu bandingkan dengan LaporanService."""

    def test_hasil_rumus_sama_dengan_laporan(self):
        lokasi = self.tulis()
        keluar = lokasi.parent / "hasil"
        profil = (lokasi.parent / "profil").as_uri()
        subprocess.run([_cari_libreoffice(), f"-env:UserInstallation={profil}", "--headless",
                        "--calc", "--convert-to", "xlsx", "--outdir", str(keluar), str(lokasi)],
                       check=True, capture_output=True, timeout=120)
        wb = load_workbook(keluar / lokasi.name, data_only=True)
        durian = self.laporan.ringkasan_jenis(self.periode.get_id_periode(),
                                              self.master.daftar_jenis()[1])
        r, bawor = durian["ringkasan"], durian["per_varietas"]["Bawor"]

        ws = wb["Durian"]
        self.assertEqual((ws["E9"].value, ws["J9"].value, ws["K9"].value),
                         (r["jumlah_stok"], r["jumlah_panen"], r["sisa"]))
        self.assertAlmostEqual(ws["L9"].value, r["total_bobot"])
        self.assertEqual(ws["K6"].value, -1)                    # sisa negatif Bawor 2
        self.assertAlmostEqual(ws["H10"].value, 2.0 + 4.6 + 3.0)  # kg tanggal 14-09
        baris = next(b for b in range(10, ws.max_row + 1) if ws[f"B{b}"].value == "Bawor")
        self.assertEqual(ws[f"D{baris}"].value, bawor["jumlah_panen"])
        self.assertAlmostEqual(ws[f"L{baris}"].value, bawor["per_keterangan"]["Baik"]["total_bobot"])
        self.assertAlmostEqual(ws[f"K{baris}"].value,
                               bawor["per_keterangan"]["Baik"]["persentase"] / 100)

        ringkasan = wb[SHEET_RINGKASAN]
        self.assertEqual([ringkasan[f"{k}7"].value for k in "ABCDE"],
                         ["Durian", 2, r["jumlah_stok"], r["jumlah_panen"], r["sisa"]])


if __name__ == "__main__":
    unittest.main()
