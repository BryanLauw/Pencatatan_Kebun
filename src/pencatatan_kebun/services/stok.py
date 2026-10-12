import sqlite3
from datetime import date

from pencatatan_kebun.models import PeriodePanen, Pohon, StokPohon
from pencatatan_kebun.repo.buah import RepoBuah
from pencatatan_kebun.repo.periode_panen import RepoPeriodePanen
from pencatatan_kebun.repo.pohon import RepoPohon
from pencatatan_kebun.repo.stok_pohon import RepoStokPohon
from pencatatan_kebun.services.exception import (
    DataSudahAdaException,
    DataTidakDitemukanException,
    JumlahBuahTidakValidException,
)
from pencatatan_kebun.services.validasi import cek_tanggal


class StokService:
    """Catat jumlah buah di setiap pohon per periode, dan hitung sisanya.

    Sisa tidak disimpan: jumlah_buah dikurangi semua catatan buah pohon itu
    di dalam rentang tanggal periode (termasuk buah gugur). Untuk periode yang
    masih aktif, rentangnya sampai hari ini.

    Semua fungsi yang mengubah data melempar ServiceException dengan pesan
    yang jelas jika input tidak valid, lalu commit dalam satu transaksi.

    Args:
        conn: Koneksi database dari buka_koneksi.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.repo_stok = RepoStokPohon(conn)
        self.repo_pohon = RepoPohon(conn)
        self.repo_periode = RepoPeriodePanen(conn)
        self.repo_buah = RepoBuah(conn)

    def _jumlah_tercatat(self, pohon: Pohon, periode: PeriodePanen) -> int:
        """Jumlah catatan buah satu pohon di dalam rentang tanggal periode.

        Args:
            pohon: Pohon yang dihitung.
            periode: Periode panen. Jika masih aktif, dihitung sampai hari ini.

        Returns:
            Jumlah catatan buah, termasuk buah gugur.
        """
        selesai = periode.get_tanggal_selesai() or date.today().isoformat()
        return self.repo_buah.count_by_pohon_date_range(
            pohon.get_id_pohon(), periode.get_tanggal_mulai(), selesai)

    def _cek_isian(self, pohon: Pohon, periode: PeriodePanen, jumlah_buah: int,
                   tanggal_hitung: str) -> None:
        """Cek semua isian sebelum mencatat atau mengubah stok.

        Dipakai bersama oleh catat_stok dan ubah_stok.

        Args:
            pohon: Objek Pohon.
            periode: Objek PeriodePanen.
            jumlah_buah: Bilangan bulat 0 atau lebih, tidak kurang dari buah
                yang sudah tercatat di periode itu.
            tanggal_hitung: Tanggal format YYYY-MM-DD, tidak boleh di masa depan.

        Raises:
            JumlahBuahTidakValidException: Jumlah bukan bilangan bulat 0 atau
                lebih, atau kurang dari buah yang sudah tercatat.
            TanggalTidakValidException: Tanggal tidak valid atau di masa depan.
            DataTidakDitemukanException: Pohon/periode sudah tidak ada di database.
        """
        if isinstance(jumlah_buah, bool) or not isinstance(jumlah_buah, int) or jumlah_buah < 0:
            raise JumlahBuahTidakValidException()

        cek_tanggal(tanggal_hitung, kolom="tanggal_hitung", boleh_masa_depan=False)

        if self.repo_pohon.read(pohon.get_id_pohon()) is None:
            raise DataTidakDitemukanException("pohon", kolom="pohon")

        periode_db = self.repo_periode.read(periode.get_id_periode())
        if periode_db is None:
            raise DataTidakDitemukanException("periode panen", kolom="periode_panen")

        tercatat = self._jumlah_tercatat(pohon, periode_db)
        if jumlah_buah < tercatat:
            raise JumlahBuahTidakValidException(
                f"Sudah ada {tercatat} buah tercatat dari pohon ini di periode {periode_db.get_nama()}")

    def catat_stok(self, pohon: Pohon, periode: PeriodePanen, jumlah_buah: int,
                   tanggal_hitung: str) -> StokPohon:
        """Catat jumlah buah di satu pohon untuk satu periode.

        Pohon dan periode dipilih dari dropdown di ui, lalu dicek masih ada di
        database.

        Args:
            pohon: Objek Pohon.
            periode: Objek PeriodePanen.
            jumlah_buah: Jumlah buah di pohon saat dihitung. Bilangan bulat 0
                atau lebih, tidak kurang dari buah yang sudah tercatat.
            tanggal_hitung: Tanggal buah dihitung, format YYYY-MM-DD, tidak
                boleh di masa depan.

        Returns:
            StokPohon yang tersimpan.

        Raises:
            JumlahBuahTidakValidException: Jumlah tidak valid.
            TanggalTidakValidException: Tanggal tidak valid atau di masa depan.
            DataTidakDitemukanException: Pohon/periode sudah tidak ada di database.
            DataSudahAdaException: Pohon sudah punya stok di periode ini.
        """
        self._cek_isian(pohon, periode, jumlah_buah, tanggal_hitung)
        if self.repo_stok.read(pohon.get_id_pohon(), periode.get_id_periode()) is not None:
            raise DataSudahAdaException(
                f"stok pohon {pohon.get_varietas().get_nama_varietas()} {pohon.get_nomor_pohon()} "
                f"di periode {periode.get_nama()}", kolom="pohon")

        stok = StokPohon(pohon, periode, jumlah_buah, tanggal_hitung)
        self.repo_stok.create(stok)
        self.conn.commit()
        return stok

    def ubah_stok(self, pohon: Pohon, periode: PeriodePanen, jumlah_buah: int,
                  tanggal_hitung: str) -> StokPohon:
        """Perbaiki jumlah buah atau tanggal hitung stok yang sudah ada.

        Pohon dan periode tidak bisa diubah karena menjadi kunci stok; untuk
        memindahkan stok, hapus lalu catat ulang.

        Args:
            pohon: Pohon pemilik stok.
            periode: Periode stok.
            jumlah_buah: Sama seperti catat_stok.
            tanggal_hitung: Sama seperti catat_stok.

        Returns:
            StokPohon setelah diubah.

        Raises:
            JumlahBuahTidakValidException: Jumlah tidak valid.
            TanggalTidakValidException: Tanggal tidak valid atau di masa depan.
            DataTidakDitemukanException: Pohon/periode sudah tidak ada, atau
                pohon belum punya stok di periode ini.
        """
        self._cek_isian(pohon, periode, jumlah_buah, tanggal_hitung)
        if self.repo_stok.read(pohon.get_id_pohon(), periode.get_id_periode()) is None:
            raise DataTidakDitemukanException("stok pohon")

        self.repo_stok.update(StokPohon(pohon, periode, jumlah_buah, tanggal_hitung))
        self.conn.commit()
        return self.repo_stok.read(pohon.get_id_pohon(), periode.get_id_periode())

    def hapus_stok(self, id_pohon: str, id_periode: str) -> None:
        """Hapus stok satu pohon di satu periode. Catatan buah tidak ikut terhapus.

        Args:
            id_pohon: Id pohon.
            id_periode: Id periode.

        Raises:
            DataTidakDitemukanException: Stok tidak ditemukan.
        """
        if self.repo_stok.read(id_pohon, id_periode) is None:
            raise DataTidakDitemukanException("stok pohon")
        self.repo_stok.delete(id_pohon, id_periode)
        self.conn.commit()

    def sisa_buah(self, id_pohon: str, id_periode: str) -> int:
        """Sisa buah di satu pohon pada satu periode.

        Args:
            id_pohon: Id pohon.
            id_periode: Id periode.

        Returns:
            jumlah_buah dikurangi buah yang sudah tercatat (termasuk gugur).

        Raises:
            DataTidakDitemukanException: Pohon belum punya stok di periode ini.
        """
        stok = self.repo_stok.read(id_pohon, id_periode)
        if stok is None:
            raise DataTidakDitemukanException("stok pohon")
        return stok.get_jumlah_buah() - self._jumlah_tercatat(stok.get_pohon(), stok.get_periode())

    def daftar_stok_periode(self, id_periode: str) -> list[dict]:
        """Stok semua pohon di satu periode beserta jumlah tercatat dan sisanya.

        Args:
            id_periode: Id periode panen.

        Returns:
            Satu dict per pohon yang punya stok:
            {"stok": StokPohon, "jumlah_tercatat": int, "sisa": int},
            urut berdasarkan jenis, varietas, lalu nomor pohon. Periode tanpa
            stok menghasilkan [].

        Raises:
            DataTidakDitemukanException: Periode tidak ditemukan.
        """
        if self.repo_periode.read(id_periode) is None:
            raise DataTidakDitemukanException("periode panen", kolom="periode_panen")

        hasil = []
        for stok in self.repo_stok.read_by_periode(id_periode):
            tercatat = self._jumlah_tercatat(stok.get_pohon(), stok.get_periode())
            hasil.append({
                "stok": stok,
                "jumlah_tercatat": tercatat,
                "sisa": stok.get_jumlah_buah() - tercatat,
            })
        return hasil
