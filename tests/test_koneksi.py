import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pencatatan_kebun.db.koneksi import buka_koneksi


class TestKoneksi(unittest.TestCase):
    def test_tabel_terbentuk(self):
        conn = buka_koneksi(":memory:")
        nama = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("jenis_tanaman", nama)
        conn.close()

    def test_foreign_key_aktif(self):
        conn = buka_koneksi(":memory:")
        self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        conn.close()

    def test_folder_dibuat_dan_data_bertahan(self):
        with tempfile.TemporaryDirectory() as folder:
            lokasi = Path(folder) / "baru" / "kebun.db"
            conn = buka_koneksi(lokasi)
            conn.execute("INSERT INTO jenis_tanaman VALUES ('j1', 'Durian', NULL)")
            conn.commit()
            conn.close()

            conn = buka_koneksi(lokasi)
            jumlah = conn.execute("SELECT COUNT(*) FROM jenis_tanaman").fetchone()[0]
            self.assertEqual(jumlah, 1)
            conn.close()


if __name__ == "__main__":
    unittest.main()
