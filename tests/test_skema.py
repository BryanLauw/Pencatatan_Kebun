import sqlite3
import unittest
import uuid
from pathlib import Path

SKEMA = Path(__file__).resolve().parents[1] / "src" / "pencatatan_kebun" / "db" / "skema.sql"


def buka_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SKEMA.read_text(encoding="utf-8"))
    return conn


def isi_induk(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO jenis_tanaman VALUES ('j1', 'Durian', NULL)")
    conn.execute("INSERT INTO varietas VALUES ('v1', 'j1', 'Musang King', NULL)")


def isi_pohon(conn: sqlite3.Connection) -> None:
    isi_induk(conn)
    conn.execute("INSERT INTO pohon VALUES ('p1', 'v1', 1)")
    conn.execute("INSERT INTO keterangan_buah VALUES ('baik', 'Baik', NULL)")


def tambah_buah(conn, id_buah="b1", id_pohon="p1", id_keterangan="baik",
                bobot=1.25, tanggal="2026-01-15"):
    return conn.execute(
        "INSERT INTO buah (id_buah, id_pohon, tanggal_panen, id_keterangan, bobot) "
        "VALUES (?, ?, ?, ?, ?)",
        (id_buah, id_pohon, tanggal, id_keterangan, bobot))


def tambah_periode(conn, id_periode, mulai, selesai, nama="Periode"):
    return conn.execute(
        "INSERT INTO periode_panen VALUES (?, ?, ?, ?, NULL)",
        (id_periode, nama, mulai, selesai))


def tambah_stok(conn, id_pohon="p1", id_periode="r1", jumlah=10, tanggal="2026-01-10"):
    return conn.execute(
        "INSERT INTO stok_pohon (id_pohon, id_periode, jumlah_buah, tanggal_hitung) "
        "VALUES (?, ?, ?, ?)",
        (id_pohon, id_periode, jumlah, tanggal))


class TestSkema(unittest.TestCase):
    def setUp(self):
        self.conn = buka_db()
        self.addCleanup(self.conn.close)

    def kolom(self, tabel: str) -> dict:
        return {r[1]: r[2] for r in self.conn.execute(f"PRAGMA table_info({tabel})")}

    # ---- struktur ----

    def test_tidak_ada_trigger_buah(self):
        nama = {r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'")}
        self.assertEqual(
            nama,
            {"periode_panen_tumpang_tindih_insert", "periode_panen_tumpang_tindih_update",
             "tutup_periode_panen"})

    def test_semua_tabel_terbentuk(self):
        nama = {r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(
            nama,
            {"jenis_tanaman", "varietas", "pohon", "keterangan_buah", "buah", "periode_panen",
             "stok_pohon"})

    def test_skema_bisa_dijalankan_dua_kali(self):
        self.conn.executescript(SKEMA.read_text(encoding="utf-8"))

    def test_semua_id_bertipe_text(self):
        for tabel, kolom in [("jenis_tanaman", "id_jenis"), ("varietas", "id_varietas"),
                             ("pohon", "id_pohon"), ("keterangan_buah", "id_keterangan"),
                             ("buah", "id_buah"), ("periode_panen", "id_periode")]:
            self.assertEqual(self.kolom(tabel)[kolom].upper(), "TEXT", tabel)

    def test_id_tidak_boleh_null(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO jenis_tanaman VALUES (NULL, 'Durian', NULL)")

    def test_id_uuid_diterima(self):
        id_jenis, id_varietas = str(uuid.uuid4()), str(uuid.uuid4())
        self.conn.execute("INSERT INTO jenis_tanaman VALUES (?, 'Durian', NULL)", (id_jenis,))
        self.conn.execute(
            "INSERT INTO varietas VALUES (?, ?, 'Musang King', NULL)", (id_varietas, id_jenis))

    def test_id_unik(self):
        isi_induk(self.conn)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO jenis_tanaman VALUES ('j1', 'Mangga', NULL)")

    def test_nomor_pohon_bertipe_angka(self):
        self.assertIn("INT", self.kolom("pohon")["nomor_pohon"].upper())

    # ---- jenis_tanaman & varietas ----

    def test_nama_jenis_wajib_diisi(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO jenis_tanaman VALUES ('j1', NULL, NULL)")

    def test_nama_jenis_tidak_boleh_kosong(self):
        for nama in ("", "   "):
            with self.assertRaises(sqlite3.IntegrityError, msg=repr(nama)):
                self.conn.execute("INSERT INTO jenis_tanaman VALUES ('j1', ?, NULL)", (nama,))

    def test_nama_jenis_unik_tanpa_membedakan_huruf(self):
        self.conn.execute("INSERT INTO jenis_tanaman VALUES ('j1', 'Durian', NULL)")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO jenis_tanaman VALUES ('j2', 'durian', NULL)")

    def test_varietas_menolak_jenis_yang_tidak_ada(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO varietas VALUES ('v1', 'xx', 'Nama', NULL)")

    def test_nama_varietas_tidak_boleh_kosong(self):
        self.conn.execute("INSERT INTO jenis_tanaman VALUES ('j1', 'Durian', NULL)")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO varietas VALUES ('v1', 'j1', '  ', NULL)")

    def test_nama_varietas_unik_per_jenis(self):
        isi_induk(self.conn)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO varietas VALUES ('v2', 'j1', 'musang king', NULL)")

    def test_nama_varietas_sama_boleh_di_jenis_lain(self):
        isi_induk(self.conn)
        self.conn.execute("INSERT INTO jenis_tanaman VALUES ('j2', 'Mangga', NULL)")
        self.conn.execute("INSERT INTO varietas VALUES ('v2', 'j2', 'Musang King', NULL)")

    # ---- pohon ----

    def test_pohon_bisa_ditambahkan(self):
        isi_pohon(self.conn)

    def test_nomor_pohon_wajib_diisi(self):
        isi_induk(self.conn)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO pohon VALUES ('p1', 'v1', NULL)")

    def test_nomor_pohon_harus_positif(self):
        isi_induk(self.conn)
        for nomor in (0, -1):
            with self.assertRaises(sqlite3.IntegrityError, msg=str(nomor)):
                self.conn.execute("INSERT INTO pohon VALUES ('p1', 'v1', ?)", (nomor,))

    def test_nomor_pohon_unik_per_varietas(self):
        isi_pohon(self.conn)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO pohon VALUES ('p2', 'v1', 1)")

    def test_nomor_pohon_sama_boleh_di_varietas_lain(self):
        isi_pohon(self.conn)
        self.conn.execute("INSERT INTO varietas VALUES ('v2', 'j1', 'Montong', NULL)")
        self.conn.execute("INSERT INTO pohon VALUES ('p2', 'v2', 1)")

    def test_pohon_wajib_punya_varietas(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO pohon (id_pohon, nomor_pohon) VALUES ('p1', 1)")

    def test_pohon_menolak_varietas_yang_tidak_ada(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO pohon VALUES ('p1', 'xx', 1)")

    def test_kolom_pohon(self):
        self.assertEqual(set(self.kolom("pohon")), {"id_pohon", "id_varietas", "nomor_pohon"})

    # ---- keterangan_buah ----

    def test_nama_keterangan_wajib_diisi_dan_tidak_kosong(self):
        for nama in (None, "", " "):
            with self.assertRaises(sqlite3.IntegrityError, msg=repr(nama)):
                self.conn.execute(
                    "INSERT INTO keterangan_buah VALUES ('baik', ?, NULL)", (nama,))

    def test_nama_keterangan_unik_tanpa_membedakan_huruf(self):
        self.conn.execute("INSERT INTO keterangan_buah VALUES ('baik', 'Baik', NULL)")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO keterangan_buah VALUES ('bagus', 'BAIK', NULL)")

    # ---- buah ----

    def test_buah_bisa_ditambahkan(self):
        isi_pohon(self.conn)
        tambah_buah(self.conn)

    def test_buah_menolak_pohon_yang_tidak_ada(self):
        isi_pohon(self.conn)
        with self.assertRaises(sqlite3.IntegrityError):
            tambah_buah(self.conn, id_pohon="xx")

    def test_buah_tidak_punya_kolom_varietas(self):
        self.assertNotIn("id_varietas", self.kolom("buah"))

    def test_jenis_varietas_boleh_dipindah_walau_dipakai_buah(self):
        isi_pohon(self.conn)
        self.conn.execute("INSERT INTO jenis_tanaman VALUES ('j2', 'Alpukat', NULL)")
        tambah_buah(self.conn)
        self.conn.execute("UPDATE varietas SET id_jenis = 'j2' WHERE id_varietas = 'v1'")

    def test_buah_menolak_keterangan_yang_tidak_ada(self):
        isi_pohon(self.conn)
        with self.assertRaises(sqlite3.IntegrityError):
            tambah_buah(self.conn, id_keterangan="asal")

    def test_buah_wajib_punya_keterangan(self):
        isi_pohon(self.conn)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO buah (id_buah, id_pohon, tanggal_panen, bobot) "
                "VALUES ('b1', 'p1', '2026-01-15', 1.0)")

    def test_buah_menolak_bobot_nol_dan_negatif(self):
        isi_pohon(self.conn)
        for bobot in (0, -1):
            with self.assertRaises(sqlite3.IntegrityError, msg=str(bobot)):
                tambah_buah(self.conn, bobot=bobot)

    def test_buah_menolak_format_tanggal_salah(self):
        isi_pohon(self.conn)
        for tanggal in ("15-01-2026", "2026-1-5", "2026/01/15", "2026-02-30", "kemarin", ""):
            with self.assertRaises(sqlite3.IntegrityError, msg=tanggal):
                tambah_buah(self.conn, tanggal=tanggal)

    def test_rata_rata_bobot_per_keterangan(self):
        isi_pohon(self.conn)
        self.conn.execute("INSERT INTO keterangan_buah VALUES ('rusak', 'Rusak', NULL)")
        tambah_buah(self.conn, "b1", id_keterangan="baik", bobot=2.0)
        tambah_buah(self.conn, "b2", id_keterangan="baik", bobot=4.0)
        tambah_buah(self.conn, "b3", id_keterangan="rusak", bobot=1.0)
        hasil = dict(self.conn.execute(
            "SELECT id_keterangan, AVG(bobot) FROM buah GROUP BY id_keterangan"))
        self.assertEqual(hasil, {"baik": 3.0, "rusak": 1.0})

    def test_hapus_induk_ditolak_jika_masih_dipakai(self):
        isi_pohon(self.conn)
        tambah_buah(self.conn)
        for tabel in ("pohon", "varietas", "jenis_tanaman", "keterangan_buah"):
            with self.assertRaises(sqlite3.IntegrityError, msg=tabel):
                self.conn.execute(f"DELETE FROM {tabel}")

    # ---- stok_pohon ----

    def test_stok_bisa_ditambahkan(self):
        isi_pohon(self.conn)
        tambah_periode(self.conn, "r1", "2026-01-01", None)
        tambah_stok(self.conn)

    def test_kunci_stok_adalah_pohon_dan_periode(self):
        kunci = {r[1]: r[5] for r in self.conn.execute("PRAGMA table_info(stok_pohon)")}
        self.assertEqual(kunci["id_pohon"], 1)
        self.assertEqual(kunci["id_periode"], 2)
        self.assertEqual(kunci["jumlah_buah"], 0)

    def test_stok_satu_pohon_satu_periode(self):
        isi_pohon(self.conn)
        tambah_periode(self.conn, "r1", "2026-01-01", "2026-03-31")
        tambah_stok(self.conn)
        with self.assertRaises(sqlite3.IntegrityError):
            tambah_stok(self.conn, jumlah=5)

    def test_stok_pohon_sama_boleh_di_periode_lain(self):
        isi_pohon(self.conn)
        tambah_periode(self.conn, "r1", "2026-01-01", "2026-03-31")
        tambah_periode(self.conn, "r2", "2026-04-01", None)
        tambah_stok(self.conn, id_periode="r1")
        tambah_stok(self.conn, id_periode="r2", tanggal="2026-04-05")

    def test_stok_menolak_pohon_atau_periode_yang_tidak_ada(self):
        isi_pohon(self.conn)
        tambah_periode(self.conn, "r1", "2026-01-01", None)
        with self.assertRaises(sqlite3.IntegrityError):
            tambah_stok(self.conn, id_pohon="xx")
        with self.assertRaises(sqlite3.IntegrityError):
            tambah_stok(self.conn, id_periode="xx")

    def test_stok_jumlah_nol_diterima_negatif_ditolak(self):
        isi_pohon(self.conn)
        tambah_periode(self.conn, "r1", "2026-01-01", None)
        tambah_stok(self.conn, jumlah=0)
        self.conn.execute("DELETE FROM stok_pohon")
        with self.assertRaises(sqlite3.IntegrityError):
            tambah_stok(self.conn, jumlah=-1)

    def test_stok_jumlah_wajib_diisi(self):
        isi_pohon(self.conn)
        tambah_periode(self.conn, "r1", "2026-01-01", None)
        with self.assertRaises(sqlite3.IntegrityError):
            tambah_stok(self.conn, jumlah=None)

    def test_stok_menolak_format_tanggal_salah(self):
        isi_pohon(self.conn)
        tambah_periode(self.conn, "r1", "2026-01-01", None)
        for tanggal in ("10-01-2026", "2026-02-30", "", None):
            with self.assertRaises(sqlite3.IntegrityError, msg=repr(tanggal)):
                tambah_stok(self.conn, tanggal=tanggal)

    def test_hapus_pohon_atau_periode_ditolak_jika_punya_stok(self):
        isi_pohon(self.conn)
        tambah_periode(self.conn, "r1", "2026-01-01", None)
        tambah_stok(self.conn)
        for tabel in ("pohon", "periode_panen"):
            with self.assertRaises(sqlite3.IntegrityError, msg=tabel):
                self.conn.execute(f"DELETE FROM {tabel}")

    def test_sisa_buah_dihitung_dari_stok_dan_catatan_buah(self):
        isi_pohon(self.conn)
        self.conn.execute("INSERT INTO keterangan_buah VALUES ('gugur', 'Gugur', NULL)")
        tambah_periode(self.conn, "r1", "2026-01-01", "2026-03-31")
        tambah_stok(self.conn, jumlah=10)
        tambah_buah(self.conn, "b1", tanggal="2026-01-15")
        tambah_buah(self.conn, "b2", id_keterangan="gugur", tanggal="2026-02-01")
        tambah_buah(self.conn, "b3", tanggal="2026-04-01")
        sisa = self.conn.execute(
            "SELECT s.jumlah_buah - COUNT(b.id_buah) FROM stok_pohon s "
            "JOIN periode_panen r ON r.id_periode = s.id_periode "
            "LEFT JOIN buah b ON b.id_pohon = s.id_pohon "
            "AND b.tanggal_panen BETWEEN r.tanggal_mulai AND r.tanggal_selesai "
            "GROUP BY s.id_pohon, s.id_periode").fetchone()[0]
        self.assertEqual(sisa, 8)

    # ---- periode_panen ----

    def test_periode_bisa_ditambahkan(self):
        tambah_periode(self.conn, "r1", "2026-01-01", "2026-03-01")

    def test_periode_menolak_tanggal_selesai_sebelum_atau_sama_dengan_mulai(self):
        for mulai, selesai in (("2026-03-01", "2026-02-01"), ("2026-03-01", "2026-03-01")):
            with self.assertRaises(sqlite3.IntegrityError, msg=f"{mulai} {selesai}"):
                tambah_periode(self.conn, "r1", mulai, selesai)

    def test_periode_menolak_format_tanggal_salah(self):
        with self.assertRaises(sqlite3.IntegrityError):
            tambah_periode(self.conn, "r1", "01-01-2026", "01-03-2026")
        with self.assertRaises(sqlite3.IntegrityError):
            tambah_periode(self.conn, "r1", "2026-01-01", "2026-3-1")
        with self.assertRaises(sqlite3.IntegrityError):
            tambah_periode(self.conn, "r1", "2026-02-30", "2026-03-31")
        with self.assertRaises(sqlite3.IntegrityError):
            tambah_periode(self.conn, "r1", "2026-01-01", "2026-02-30")

    def test_tanggal_kabisat_diterima(self):
        isi_pohon(self.conn)
        tambah_buah(self.conn, tanggal="2024-02-29")
        tambah_periode(self.conn, "r1", "2024-02-29", "2024-03-31")

    def test_periode_nama_tidak_boleh_kosong(self):
        with self.assertRaises(sqlite3.IntegrityError):
            tambah_periode(self.conn, "r1", "2026-01-01", "2026-03-01", nama="  ")

    def test_periode_menolak_tumpang_tindih_saat_tambah(self):
        tambah_periode(self.conn, "r1", "2026-03-01", "2026-05-31")
        kasus = {
            "mulai di dalam": ("2026-04-01", "2026-06-30"),
            "selesai di dalam": ("2026-01-01", "2026-03-15"),
            "membungkus": ("2026-01-01", "2026-12-31"),
            "terkandung": ("2026-04-01", "2026-04-30"),
            "sama persis": ("2026-03-01", "2026-05-31"),
            "bersentuhan di akhir": ("2026-05-31", "2026-07-01"),
            "bersentuhan di awal": ("2026-01-01", "2026-03-01"),
        }
        for nama, (mulai, selesai) in kasus.items():
            with self.assertRaises(sqlite3.IntegrityError, msg=nama):
                tambah_periode(self.conn, "r2", mulai, selesai)

    def test_periode_bersebelahan_tanpa_tumpang_tindih_diterima(self):
        tambah_periode(self.conn, "r1", "2026-03-01", "2026-05-31")
        tambah_periode(self.conn, "r2", "2026-06-01", "2026-08-31")
        tambah_periode(self.conn, "r3", "2025-01-01", "2025-12-31")

    def test_periode_menolak_tumpang_tindih_saat_diubah(self):
        tambah_periode(self.conn, "r1", "2026-01-01", "2026-02-28")
        tambah_periode(self.conn, "r2", "2026-06-01", "2026-08-31")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "UPDATE periode_panen SET tanggal_mulai = '2026-02-01' WHERE id_periode = 'r2'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "UPDATE periode_panen SET tanggal_selesai = '2026-07-01' WHERE id_periode = 'r1'")

    def test_periode_boleh_mengubah_dirinya_sendiri(self):
        tambah_periode(self.conn, "r1", "2026-01-01", "2026-02-28")
        self.conn.execute(
            "UPDATE periode_panen SET tanggal_selesai = '2026-03-31' WHERE id_periode = 'r1'")
        self.conn.execute(
            "UPDATE periode_panen SET nama_periode = 'Baru' WHERE id_periode = 'r1'")

    # ---- periode_panen: tanggal_selesai kosong (periode masih berjalan) ----

    def selesai(self, id_periode: str):
        return self.conn.execute(
            "SELECT tanggal_selesai FROM periode_panen WHERE id_periode = ?",
            (id_periode,)).fetchone()[0]

    def jumlah_periode_terbuka(self) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM periode_panen WHERE tanggal_selesai IS NULL").fetchone()[0]

    def test_periode_boleh_belum_selesai(self):
        tambah_periode(self.conn, "r1", "2026-01-01", None)
        self.assertIsNone(self.selesai("r1"))

    def test_periode_baru_menutup_periode_terbuka_otomatis(self):
        tambah_periode(self.conn, "r1", "2026-01-01", None)
        tambah_periode(self.conn, "r2", "2026-06-01", "2026-08-31")
        self.assertEqual(self.selesai("r1"), "2026-05-31")
        self.assertEqual(self.selesai("r2"), "2026-08-31")

    def test_periode_terbuka_baru_menutup_periode_terbuka_lama(self):
        tambah_periode(self.conn, "r1", "2026-01-01", None)
        tambah_periode(self.conn, "r2", "2026-06-01", None)
        self.assertEqual(self.selesai("r1"), "2026-05-31")
        self.assertIsNone(self.selesai("r2"))
        self.assertEqual(self.jumlah_periode_terbuka(), 1)

    def test_hanya_satu_periode_terbuka_setelah_beberapa_kali_tambah(self):
        for i, mulai in enumerate(("2026-01-01", "2026-04-01", "2026-07-01", "2026-10-01")):
            tambah_periode(self.conn, f"r{i}", mulai, None)
        self.assertEqual(self.jumlah_periode_terbuka(), 1)
        self.assertEqual(self.selesai("r0"), "2026-03-31")
        self.assertEqual(self.selesai("r1"), "2026-06-30")
        self.assertEqual(self.selesai("r2"), "2026-09-30")

    def test_periode_lama_sebelum_periode_terbuka_diterima(self):
        tambah_periode(self.conn, "r1", "2026-06-01", None)
        tambah_periode(self.conn, "r2", "2025-01-01", "2025-12-31")
        self.assertIsNone(self.selesai("r1"))
        self.assertEqual(self.selesai("r2"), "2025-12-31")

    def test_periode_lama_yang_menyentuh_awal_periode_terbuka_ditolak(self):
        tambah_periode(self.conn, "r1", "2026-06-01", None)
        with self.assertRaises(sqlite3.IntegrityError):
            tambah_periode(self.conn, "r2", "2025-01-01", "2026-06-01")
        self.assertIsNone(self.selesai("r1"))

    def test_periode_mulai_sama_dengan_periode_terbuka_ditolak(self):
        tambah_periode(self.conn, "r1", "2026-06-01", None)
        with self.assertRaises(sqlite3.IntegrityError):
            tambah_periode(self.conn, "r2", "2026-06-01", "2026-08-31")
        self.assertIsNone(self.selesai("r1"))
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM periode_panen").fetchone()[0], 1)

    def test_periode_terbuka_bisa_ditutup_lewat_update(self):
        tambah_periode(self.conn, "r1", "2026-01-01", None)
        self.conn.execute(
            "UPDATE periode_panen SET tanggal_selesai = '2026-12-31' WHERE id_periode = 'r1'")
        self.assertEqual(self.selesai("r1"), "2026-12-31")
        self.assertEqual(self.jumlah_periode_terbuka(), 0)

    def test_periode_tertutup_tidak_bisa_dibuka_kembali_jika_bertumpuk(self):
        tambah_periode(self.conn, "r1", "2026-01-01", "2026-02-28")
        tambah_periode(self.conn, "r2", "2026-06-01", "2026-08-31")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "UPDATE periode_panen SET tanggal_selesai = NULL WHERE id_periode = 'r1'")
        self.assertEqual(self.selesai("r1"), "2026-02-28")

    def test_periode_terakhir_bisa_dibuka_kembali(self):
        tambah_periode(self.conn, "r1", "2026-01-01", "2026-02-28")
        self.conn.execute(
            "UPDATE periode_panen SET tanggal_selesai = NULL WHERE id_periode = 'r1'")
        self.assertIsNone(self.selesai("r1"))

    def test_periode_terbuka_menolak_tanggal_mulai_dipindah_ke_periode_lain(self):
        tambah_periode(self.conn, "r1", "2026-01-01", "2026-02-28")
        tambah_periode(self.conn, "r2", "2026-06-01", None)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "UPDATE periode_panen SET tanggal_mulai = '2026-02-01' WHERE id_periode = 'r2'")


if __name__ == "__main__":
    unittest.main()
