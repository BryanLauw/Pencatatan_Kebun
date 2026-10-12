import sqlite3
from datetime import date

from pencatatan_kebun.models import PeriodePanen
from pencatatan_kebun.repo.periode_panen import RepoPeriodePanen
from pencatatan_kebun.services.exception import (
    DataMasihDipakaiException,
    DataSudahAdaException,
    DataTidakDitemukanException,
    NamaKosongException,
    PeriodeBertumpukException,
    PeriodeSudahDitutupException,
    TanggalTidakValidException,
)
from pencatatan_kebun.services.validasi import cek_tanggal


class PeriodeService:
    """Kelola periode panen.

    Aturan yang sudah dijaga skema: periode tidak boleh tumpang tindih, dan
    membuka periode baru otomatis menutup periode yang masih aktif. Service ini
    memeriksa lebih awal agar pesannya jelas, lalu commit dalam satu transaksi.

    Args:
        conn: Koneksi database dari buka_koneksi.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.repo_periode = RepoPeriodePanen(conn)

    def _cek_periode(self, nama: str, tanggal_mulai: str, tanggal_selesai: str | None, id_periode: str | None = None) -> None:
        """Cek nama dan tanggal periode sebelum disimpan.

        Args:
            nama: Nama periode, mis. "Raya 2026". Wajib diisi.
            tanggal_mulai: Tanggal format YYYY-MM-DD.
            tanggal_selesai: Tanggal format YYYY-MM-DD, atau None jika masih aktif.
            id_periode: Id periode yang sedang diubah, atau None jika baru.

        Raises:
            NamaKosongException: Nama kosong.
            TanggalTidakValidException: Tanggal tidak valid, atau tanggal_selesai
                tidak setelah tanggal_mulai.
            DataSudahAdaException: Periode sudah ada.
            PeriodeBertumpukException: Bertumpuk dengan periode lain.
        """
        if nama is None or nama.strip() == "":
            raise NamaKosongException("Nama periode", kolom="nama_periode")
        cek_tanggal(tanggal_mulai, kolom="tanggal_mulai")
        if tanggal_selesai is not None:
            cek_tanggal(tanggal_selesai, kolom="tanggal_selesai")

        if tanggal_selesai is not None and tanggal_selesai <= tanggal_mulai:
            raise TanggalTidakValidException(
                "Tanggal selesai harus setelah tanggal mulai",
                kolom="tanggal_selesai"
            )

        ada = self.repo_periode.read_by_name(nama.strip())
        if ada is not None and ada.get_id_periode() != id_periode:
            raise DataSudahAdaException(nama.strip(), kolom="nama_periode")

        selesai = tanggal_selesai if tanggal_selesai is not None else "9999-12-31"
        for lain in self.repo_periode.read_by_range(tanggal_mulai, selesai):
            if lain.get_id_periode() == id_periode:
                continue
            if id_periode is None and lain.get_tanggal_selesai() is None and lain.get_tanggal_mulai() < tanggal_mulai:
                continue
            raise PeriodeBertumpukException(nama, lain.get_nama(), kolom="tanggal_mulai")

    def buka_periode(self, nama: str, tanggal_mulai: str, tanggal_selesai: str | None = None, deskripsi: str = "") -> PeriodePanen:
        """Mulai periode panen baru yang masih berjalan.

        Periode aktif sebelumnya otomatis ditutup sehari sebelum tanggal_mulai.

        Args:
            nama: Nama periode, mis. "Raya 2026". Wajib diisi.
            tanggal_mulai: Tanggal format YYYY-MM-DD.
            tanggal_selesai: Tanggal format YYYY-MM-DD, atau None jika masih aktif.
            deskripsi: Keterangan tambahan, boleh kosong.

        Returns:
            PeriodePanen yang tersimpan.

        Raises:
            NamaKosongException: Nama kosong.
            TanggalTidakValidException: Tanggal tidak valid, atau tanggal_selesai
                tidak setelah tanggal_mulai.
            PeriodeBertumpukException: Bertumpuk dengan periode lain.
        """
        self._cek_periode(nama, tanggal_mulai, tanggal_selesai)

        periode = PeriodePanen(nama.strip(), tanggal_mulai, tanggal_selesai, deskripsi)
        self.repo_periode.create(periode)
        self.conn.commit()
        return periode

    def tutup_periode(self, id_periode: str, tanggal_selesai: str | None = None) -> PeriodePanen:
        """Tutup periode yang masih aktif. Tanggal selesai bisa di masa lalu.
        Jika tanggal selesai None, otomatis mengisi tanggal selesai pada hari ini.

        Args:
            id_periode: Id periode yang ditutup.
            tanggal_selesai: Tanggal format YYYY-MM-DD, harus setelah tanggal mulai.

        Returns:
            PeriodePanen setelah ditutup.

        Raises:
            DataTidakDitemukanException: Periode tidak ditemukan.
            PeriodeSudahDitutupException: Periode sudah ditutup.
            TanggalTidakValidException: tanggal_selesai tidak valid.
        """
        if not tanggal_selesai:
            tanggal_selesai = date.today().isoformat()

        periode = self.repo_periode.read(id_periode)
        if periode is None:
            raise DataTidakDitemukanException("periode panen", kolom="periode_panen")
        if periode.get_tanggal_selesai() is not None:
            raise PeriodeSudahDitutupException(periode.get_nama())

        self._cek_periode(periode.get_nama(), periode.get_tanggal_mulai(), tanggal_selesai, id_periode=id_periode)

        periode.set_tanggal_selesai(tanggal_selesai)
        self.repo_periode.update(periode)
        self.conn.commit()
        return periode        

    def ubah_periode(self, id_periode: str, nama: str, tanggal_mulai: str,
                     tanggal_selesai: str | None, deskripsi: str = "") -> PeriodePanen:
        """Ubah data periode.

        Args:
            id_periode: Id periode yang diubah.
            nama: Nama baru. Wajib diisi.
            tanggal_mulai: Tanggal format YYYY-MM-DD.
            tanggal_selesai: Tanggal format YYYY-MM-DD, atau None jika masih aktif.
            deskripsi: Deskripsi baru.

        Returns:
            PeriodePanen setelah diubah.

        Raises:
            DataTidakDitemukanException: Periode tidak ditemukan.
            NamaKosongException: Nama kosong.
            TanggalTidakValidException: Tanggal tidak valid, atau tanggal_selesai
                tidak setelah tanggal_mulai.
            PeriodeBertumpukException: Bertumpuk dengan periode lain.
        """
        if self.repo_periode.read(id_periode) is None:
            raise DataTidakDitemukanException(f"periode panen dengan id {id_periode}", kolom="id_periode")
        self._cek_periode(nama, tanggal_mulai, tanggal_selesai, id_periode=id_periode)

        periode = PeriodePanen(nama.strip(), tanggal_mulai, tanggal_selesai, deskripsi, id_periode=id_periode)
        self.repo_periode.update(periode)
        self.conn.commit()
        return periode

    def hapus_periode(self, id_periode: str) -> None:
        """Hapus periode. Catatan buah di dalamnya tidak ikut terhapus.

        Args:
            id_periode: Id periode yang dihapus.

        Raises:
            DataTidakDitemukanException: Periode tidak ditemukan.
            DataMasihDipakaiException: Periode sudah punya stok pohon.
        """
        periode = self.repo_periode.read(id_periode)
        if periode is None:
            raise DataTidakDitemukanException(f"periode panen dengan id {id_periode}", kolom="id_periode")
        if self.repo_periode.is_periode_used(id_periode):
            raise DataMasihDipakaiException(f"periode panen {periode.get_nama()}", kolom="id_periode")

        self.repo_periode.delete(id_periode)
        self.conn.commit()

    def periode_aktif(self) -> PeriodePanen | None:
        """Periode yang sedang berjalan (tanggal selesai kosong).

        Returns:
            PeriodePanen yang aktif, atau None jika tidak ada.
        """
        return self.repo_periode.read_active_period()

    def periode_pada_tanggal(self, tanggal: str) -> PeriodePanen | None:
        """Periode yang mencakup satu tanggal.

        Args:
            tanggal: Tanggal format YYYY-MM-DD, mis. tanggal panen sebuah buah.

        Returns:
            PeriodePanen yang mencakup tanggal, atau None jika di luar semua periode.

        Raises:
            TanggalTidakValidException: Tanggal tidak valid.
        """
        cek_tanggal(tanggal, kolom="tanggal", boleh_masa_depan=False)
        return self.repo_periode.read_by_date(tanggal)

    def daftar_periode(self) -> list[PeriodePanen]:
        """Semua periode.

        Returns:
            Daftar PeriodePanen, urut berdasarkan tanggal mulai.
        """
        return self.repo_periode.read_all()
