import sys
import unittest
import uuid
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pencatatan_kebun.models import (
    Buah,
    JenisTanaman,
    KeteranganBuah,
    PeriodePanen,
    Pohon,
    StokPohon,
    Varietas,
)


class TestModels(unittest.TestCase):
    def setUp(self):
        self.jenis = JenisTanaman("Durian", "Buah berduri", id_jenis="jenis-1")
        self.varietas = Varietas("Musang King", self.jenis, "Daging kuning", id_varietas="var-1")
        self.baik = KeteranganBuah("Baik", id_keterangan="baik")
        self.busuk = KeteranganBuah("Busuk", "Tidak layak jual", id_keterangan="busuk")

    def semua_objek_baru(self):
        pohon = Pohon(1, self.varietas)
        return [
            (JenisTanaman("A"), "get_id_jenis"),
            (Varietas("A", self.jenis), "get_id_varietas"),
            (pohon, "get_id_pohon"),
            (Buah(pohon, 1.0, self.baik, "2026-01-15"), "get_id_buah"),
            (PeriodePanen("A", "2026-01-01", "2026-02-01"), "get_id_periode"),
            (KeteranganBuah("A"), "get_id_keterangan"),
        ]

    def test_id_dibuat_otomatis_berupa_uuid(self):
        for objek, getter in self.semua_objek_baru():
            id_objek = getattr(objek, getter)()
            self.assertIsInstance(id_objek, str, getter)
            self.assertEqual(str(uuid.UUID(id_objek)), id_objek, getter)

    def test_id_otomatis_unik_tiap_objek(self):
        id_pertama = [getattr(o, g)() for o, g in self.semua_objek_baru()]
        id_kedua = [getattr(o, g)() for o, g in self.semua_objek_baru()]
        self.assertEqual(len(set(id_pertama + id_kedua)), 12)

    def test_id_yang_diberikan_dipakai_apa_adanya(self):
        self.assertEqual(self.jenis.get_id_jenis(), "jenis-1")
        self.assertEqual(self.varietas.get_id_varietas(), "var-1")
        self.assertEqual(Pohon(1, self.varietas, id_pohon="pohon-1").get_id_pohon(), "pohon-1")
        pohon = Pohon(1, self.varietas)
        buah = Buah(pohon, 1.0, self.baik, "2026-01-15", id_buah="buah-1")
        self.assertEqual(buah.get_id_buah(), "buah-1")
        self.assertEqual(
            PeriodePanen("A", "2026-01-01", "2026-02-01", id_periode="per-1").get_id_periode(),
            "per-1")
        self.assertEqual(self.baik.get_id_keterangan(), "baik")

    def test_id_uuid_diterima(self):
        id_uuid = str(uuid.uuid4())
        self.assertEqual(JenisTanaman("A", id_jenis=id_uuid).get_id_jenis(), id_uuid)

    def test_id_tidak_punya_setter(self):
        for objek, getter in self.semua_objek_baru():
            setter = getter.replace("get_", "set_")
            self.assertFalse(hasattr(objek, setter), setter)

    def test_jenis_tanaman(self):
        self.assertEqual(self.jenis.get_nama_jenis(), "Durian")
        self.assertEqual(self.jenis.get_deskripsi(), "Buah berduri")
        self.jenis.set_nama_jenis("Mangga")
        self.jenis.set_deskripsi("Manis")
        self.assertEqual(self.jenis.get_nama_jenis(), "Mangga")
        self.assertEqual(self.jenis.get_deskripsi(), "Manis")

    def test_varietas(self):
        self.assertEqual(self.varietas.get_nama_varietas(), "Musang King")
        self.assertIs(self.varietas.get_jenis(), self.jenis)
        self.assertEqual(self.varietas.get_deskripsi(), "Daging kuning")
        lain = JenisTanaman("Mangga", "")
        self.varietas.set_jenis(lain)
        self.varietas.set_nama_varietas("Arumanis")
        self.varietas.set_deskripsi("Harum")
        self.assertIs(self.varietas.get_jenis(), lain)
        self.assertEqual(self.varietas.get_nama_varietas(), "Arumanis")
        self.assertEqual(self.varietas.get_deskripsi(), "Harum")

    def test_pohon(self):
        pohon = Pohon(7, self.varietas)
        self.assertEqual(pohon.get_nomor_pohon(), 7)
        self.assertIs(pohon.get_varietas(), self.varietas)
        pohon.set_nomor_pohon(8)
        d24 = Varietas("D24", self.jenis)
        pohon.set_varietas(d24)
        self.assertEqual(pohon.get_nomor_pohon(), 8)
        self.assertIs(pohon.get_varietas(), d24)
        self.assertIs(pohon.get_varietas().get_jenis(), self.jenis)

    def test_keterangan_buah(self):
        self.assertEqual(self.baik.get_id_keterangan(), "baik")
        self.assertEqual(self.baik.get_nama_keterangan(), "Baik")
        self.assertEqual(self.baik.get_deskripsi(), "")
        self.assertEqual(self.busuk.get_deskripsi(), "Tidak layak jual")
        self.baik.set_nama_keterangan("Bagus")
        self.baik.set_deskripsi("Mulus")
        self.assertEqual(self.baik.get_id_keterangan(), "baik")
        self.assertEqual(self.baik.get_nama_keterangan(), "Bagus")
        self.assertEqual(self.baik.get_deskripsi(), "Mulus")

    def test_buah(self):
        pohon = Pohon(7, self.varietas)
        buah = Buah(pohon, 1.5, self.baik, "2026-01-15")
        self.assertIs(buah.get_pohon(), pohon)
        self.assertIs(buah.get_pohon().get_varietas(), self.varietas)
        self.assertFalse(hasattr(buah, "get_varietas"))
        self.assertEqual(buah.get_bobot(), 1.5)
        self.assertIs(buah.get_keterangan(), self.baik)
        self.assertEqual(buah.get_tanggal_panen(), "2026-01-15")
        lain = Pohon(9, self.varietas)
        buah.set_pohon(lain)
        buah.set_bobot(2.0)
        buah.set_keterangan(self.busuk)
        buah.set_tanggal_panen("2026-02-01")
        self.assertIs(buah.get_pohon(), lain)
        self.assertEqual(buah.get_bobot(), 2.0)
        self.assertIs(buah.get_keterangan(), self.busuk)
        self.assertEqual(buah.get_tanggal_panen(), "2026-02-01")

    def test_stok_pohon(self):
        pohon = Pohon(7, self.varietas)
        periode = PeriodePanen("Raya 2026", "2026-01-01")
        stok = StokPohon(pohon, periode, 11, "2026-01-05")
        self.assertIs(stok.get_pohon(), pohon)
        self.assertIs(stok.get_periode(), periode)
        self.assertEqual(stok.get_jumlah_buah(), 11)
        self.assertEqual(stok.get_tanggal_hitung(), "2026-01-05")
        stok.set_jumlah_buah(0)
        stok.set_tanggal_hitung("2026-01-06")
        self.assertEqual(stok.get_jumlah_buah(), 0)
        self.assertEqual(stok.get_tanggal_hitung(), "2026-01-06")

    def test_stok_pohon_kunci_tidak_punya_setter(self):
        stok = StokPohon(Pohon(7, self.varietas), PeriodePanen("A", "2026-01-01"), 1, "2026-01-05")
        for atribut in ("set_pohon", "set_periode", "get_id_stok"):
            self.assertFalse(hasattr(stok, atribut), atribut)

    def test_periode_panen_belum_selesai(self):
        p = PeriodePanen("Raya 2026", "2026-01-01", None)
        self.assertIsNone(p.get_tanggal_selesai())
        p.set_tanggal_selesai("2026-03-01")
        self.assertEqual(p.get_tanggal_selesai(), "2026-03-01")
        p.set_tanggal_selesai(None)
        self.assertIsNone(p.get_tanggal_selesai())

    def test_periode_panen_tanggal_selesai_bawaan_kosong(self):
        p = PeriodePanen("Raya 2026", "2026-01-01")
        self.assertIsNone(p.get_tanggal_selesai())
        self.assertTrue(p.is_active())

    def test_periode_panen(self):
        p = PeriodePanen("Raya 2026", "2026-01-01", "2026-03-01")
        self.assertEqual(p.get_nama(), "Raya 2026")
        self.assertEqual(p.get_tanggal_mulai(), "2026-01-01")
        self.assertEqual(p.get_tanggal_selesai(), "2026-03-01")
        self.assertEqual(p.get_deskripsi(), "")
        p.set_nama("Susulan")
        p.set_tanggal_mulai("2026-04-01")
        p.set_tanggal_selesai("2026-05-01")
        p.set_deskripsi("Panen kedua")
        self.assertEqual(p.get_nama(), "Susulan")
        self.assertEqual(p.get_tanggal_mulai(), "2026-04-01")
        self.assertEqual(p.get_tanggal_selesai(), "2026-05-01")
        self.assertEqual(p.get_deskripsi(), "Panen kedua")

    def test_periode_panen_aktif(self):
        hari_ini = date.today()
        kemarin = (hari_ini - timedelta(days=1)).isoformat()
        besok = (hari_ini + timedelta(days=1)).isoformat()
        self.assertTrue(PeriodePanen("A", "2026-01-01", None).is_active())
        self.assertTrue(PeriodePanen("A", "2000-01-01", besok).is_active())
        self.assertTrue(PeriodePanen("A", "2000-01-01", hari_ini.isoformat()).is_active())
        self.assertFalse(PeriodePanen("A", "2000-01-01", kemarin).is_active())


if __name__ == "__main__":
    unittest.main()
