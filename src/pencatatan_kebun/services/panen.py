from datetime import date
import sqlite3

from pencatatan_kebun.models import Buah, KeteranganBuah, Pohon, Varietas
from pencatatan_kebun.repo.buah import RepoBuah
from pencatatan_kebun.repo.keterangan_buah import RepoKeteranganBuah
from pencatatan_kebun.repo.periode_panen import RepoPeriodePanen
from pencatatan_kebun.repo.pohon import RepoPohon
from pencatatan_kebun.repo.varietas import RepoVarietas
from pencatatan_kebun.services.exception import BobotTidakValidException, DataTidakDitemukanException
from pencatatan_kebun.services.validasi import cek_tanggal


class PanenService:
    """Catat, ubah, hapus, dan tampilkan catatan buah hasil panen.

    Semua fungsi yang mengubah data melempar ServiceException dengan pesan
    yang jelas jika input tidak valid, lalu commit dalam satu transaksi.

    Args:
        conn: Koneksi database dari buka_koneksi.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.repo_buah = RepoBuah(conn)
        self.repo_pohon = RepoPohon(conn)
        self.repo_varietas = RepoVarietas(conn)
        self.repo_keterangan = RepoKeteranganBuah(conn)
        self.repo_periode = RepoPeriodePanen(conn)


    def _cek_isian(self, pohon: Pohon, varietas: Varietas, keterangan_buah: KeteranganBuah,
                    bobot: float, tanggal_panen: str) -> None:
        """Cek semua isian sebelum mencatat atau mengubah catatan buah.

        Dipakai bersama oleh catat_buah dan ubah_catatan_buah.

        Args:
            pohon: Objek Pohon asal buah.
            varietas: Objek Varietas buah.
            keterangan_buah: Objek KeteranganBuah, kondisi buah.
            bobot: Bobot buah dalam kg, harus lebih dari 0.
            tanggal_panen: Tanggal format YYYY-MM-DD, tidak boleh di masa depan.

        Raises:
            BobotTidakValidException: Bobot bukan angka atau tidak lebih dari 0.
            TanggalTidakValidException: Tanggal tidak valid atau di masa depan.
            DataTidakDitemukanException: Pohon/varietas/keterangan sudah tidak
                ada di database (mis. dihapus di menu lain).
        """
        if isinstance(bobot, bool) or not isinstance(bobot, (int, float)) or bobot <= 0:
            raise BobotTidakValidException()

        cek_tanggal(tanggal_panen, kolom="tanggal_panen", boleh_masa_depan=False)

        if not self.repo_pohon.read(pohon.get_id_pohon()):
            raise DataTidakDitemukanException("pohon", kolom="pohon")

        if not self.repo_varietas.read(varietas.get_id_varietas()):
            raise DataTidakDitemukanException("varietas", kolom="varietas")

        if not self.repo_keterangan.read(keterangan_buah.get_id_keterangan()):
            raise DataTidakDitemukanException("keterangan buah", kolom="keterangan_buah")


    def catat_buah(self, pohon: Pohon, varietas: Varietas, keterangan_buah: KeteranganBuah,
                   bobot: float, tanggal_panen: str) -> Buah:
        """Catat satu buah hasil panen.

        Pohon, varietas, dan keterangan dipilih dari data master (dropdown di ui),
        lalu dicek masih ada di database. Jenis tanaman tidak perlu dikirim
        karena sudah ada di varietas.get_jenis().

        Args:
            pohon: Objek Pohon asal buah.
            varietas: Objek Varietas buah.
            keterangan_buah: Objek KeteranganBuah, kondisi buah.
            bobot: Bobot buah dalam kg, harus lebih dari 0.
            tanggal_panen: Tanggal format YYYY-MM-DD, tidak boleh di masa depan.

        Returns:
            Buah yang tersimpan.

        Raises:
            BobotTidakValidException: Bobot bukan angka atau tidak lebih dari 0.
            TanggalTidakValidException: Tanggal tidak valid atau di masa depan.
            DataTidakDitemukanException: Pohon/varietas/keterangan sudah tidak
                ada di database (mis. dihapus di menu lain).
        """
        self._cek_isian(pohon, varietas, keterangan_buah, bobot, tanggal_panen)

        buah = Buah(pohon, varietas, bobot, keterangan_buah, tanggal_panen)
        self.repo_buah.create(buah)
        self.conn.commit()
        return buah


    def ubah_catatan_buah(self, id_buah: str, pohon: Pohon, varietas: Varietas,
                          keterangan_buah: KeteranganBuah, bobot: float,
                          tanggal_panen: str) -> Buah:
        """Perbaiki catatan buah yang salah input.

        Args:
            id_buah: Id catatan buah yang diubah.
            pohon: Sama seperti catat_buah.
            varietas: Sama seperti catat_buah.
            keterangan_buah: Sama seperti catat_buah.
            bobot: Sama seperti catat_buah.
            tanggal_panen: Sama seperti catat_buah.

        Returns:
            Buah setelah diubah.

        Raises:
            BobotTidakValidException: Bobot bukan angka atau tidak lebih dari 0.
            TanggalTidakValidException: Tanggal tidak valid atau di masa depan.
            DataTidakDitemukanException: Catatan buah tidak ditemukan, atau
                pohon/varietas/keterangan sudah tidak ada di database.
        """
        self._cek_isian(pohon, varietas, keterangan_buah, bobot, tanggal_panen)
        
        if not self.repo_buah.read(id_buah):
            raise DataTidakDitemukanException("catatan buah")

        self.repo_buah.update(Buah(pohon, varietas, bobot, keterangan_buah, tanggal_panen, id_buah=id_buah))
        self.conn.commit()
        return self.repo_buah.read(id_buah)
    

    def hapus_catatan_buah(self, id_buah: str) -> None:
        """Hapus satu catatan buah.

        Args:
            id_buah: Id catatan buah yang dihapus.

        Raises:
            DataTidakDitemukanException: Catatan buah tidak ditemukan.
        """
        if not self.repo_buah.read(id_buah):
            raise DataTidakDitemukanException("catatan buah")
        self.repo_buah.delete(id_buah)
        self.conn.commit()
    

    def daftar_buah_per_tanggal(self, tanggal_panen: str) -> list[Buah]:
        """Semua buah yang dipanen pada satu tanggal.

        Args:
            tanggal_panen: Tanggal format YYYY-MM-DD.

        Returns:
            Daftar Buah, urut berdasarkan nomor pohon.

        Raises:
            TanggalTidakValidException: Tanggal tidak valid.
        """
        cek_tanggal(tanggal_panen, kolom="tanggal_panen")
        return self.repo_buah.read_by_harvest_date(tanggal_panen)

    def daftar_buah_per_periode(self, id_periode: str) -> list[Buah]:
        """Semua buah yang dipanen di dalam satu periode panen.

        Args:
            id_periode: Id periode panen. Jika periode masih aktif (tanggal
                selesai kosong), diambil sampai hari ini.

        Returns:
            Daftar Buah, urut berdasarkan tanggal lalu nomor pohon.

        Raises:
            DataTidakDitemukanException: Periode tidak ditemukan.
        """
        periode = self.repo_periode.read(id_periode)
        if not periode:
            raise DataTidakDitemukanException("periode panen", kolom="periode_panen")
        
        mulai = periode.get_tanggal_mulai()
        if periode.get_tanggal_selesai():
            selesai = periode.get_tanggal_selesai()
        else:
            selesai = str(date.today())
        
        return self.repo_buah.read_by_harvest_date_range(mulai, selesai)
