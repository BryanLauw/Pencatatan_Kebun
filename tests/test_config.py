import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pencatatan_kebun import config
from pencatatan_kebun.app import jalankan


class TestConfig(unittest.TestCase):
    def test_folder_data_memakai_appdata(self):
        with mock.patch.dict(os.environ, {"APPDATA": "C:/pengguna/AppData"}):
            self.assertEqual(
                config.folder_data(), Path("C:/pengguna/AppData") / config.NAMA_APLIKASI)

    def test_folder_data_cadangan_ke_folder_rumah(self):
        env = {k: v for k, v in os.environ.items() if k != "APPDATA"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(config.folder_data(), Path.home() / config.NAMA_APLIKASI)

    def test_lokasi_db_ada_di_folder_data(self):
        with mock.patch.dict(os.environ, {"APPDATA": "C:/pengguna/AppData"}):
            self.assertEqual(config.lokasi_db(), config.folder_data() / "kebun.db")

    def test_format_tanggal_tampil(self):
        from datetime import date
        self.assertEqual(date(2026, 1, 5).strftime(config.FORMAT_TANGGAL_TAMPIL), "05-01-2026")


class TestApp(unittest.TestCase):
    def setUp(self):
        # Jendela diganti tiruan agar tes tidak tertahan di mainloop.
        patcher = mock.patch("pencatatan_kebun.app.JendelaUtama")
        self.jendela = patcher.start()
        self.addCleanup(patcher.stop)

    def test_jalankan_membuat_database_di_lokasi_yang_diberikan(self):
        with tempfile.TemporaryDirectory() as folder:
            lokasi = Path(folder) / "data" / "kebun.db"
            jalankan(lokasi)
            self.assertTrue(lokasi.exists())

    def test_jalankan_memakai_lokasi_dari_config_secara_bawaan(self):
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.dict(os.environ, {"APPDATA": folder}):
                jalankan()
            self.assertTrue((Path(folder) / config.NAMA_APLIKASI / "kebun.db").exists())

    def test_jalankan_membuka_jendela_utama(self):
        with tempfile.TemporaryDirectory() as folder:
            jalankan(Path(folder) / "kebun.db")
        self.jendela.return_value.mainloop.assert_called_once()

    def test_koneksi_ditutup_walau_ui_error(self):
        self.jendela.return_value.mainloop.side_effect = RuntimeError("ui rusak")
        with (tempfile.TemporaryDirectory() as folder,
              mock.patch("pencatatan_kebun.app.buka_koneksi") as buka):
            with self.assertRaises(RuntimeError):
                jalankan(Path(folder) / "kebun.db")
            buka.return_value.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
