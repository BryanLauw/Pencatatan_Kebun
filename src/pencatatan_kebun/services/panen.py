import sqlite3
from datetime import date

from pencatatan_kebun.models import Buah
from pencatatan_kebun.repo.buah import RepoBuah
from pencatatan_kebun.repo.jenis_tanaman import RepoJenisTanaman
from pencatatan_kebun.repo.keterangan_buah import RepoKeteranganBuah
from pencatatan_kebun.repo.pohon import RepoPohon
from pencatatan_kebun.repo.varietas import RepoVarietas


class PanenException(Exception):
    """Kesalahan yang pesannya boleh langsung ditampilkan ke pengguna."""


class PanenService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.repo_buah = RepoBuah(conn)
        self.repo_pohon = RepoPohon(conn)
        self.repo_jenis = RepoJenisTanaman(conn)
        self.repo_varietas = RepoVarietas(conn)
        self.repo_keterangan = RepoKeteranganBuah(conn)

    def catat_buah(self, nomor_pohon: int, nama_jenis: str, nama_varietas: str,
                   nama_keterangan: str, bobot: float, tanggal_panen: str) -> Buah:
        # 1. periksa input dan beri pesan yang jelas
        if bobot <= 0:
            raise PanenException("Bobot harus lebih dari 0")
        try:
            tanggal = date.fromisoformat(tanggal_panen)
        except ValueError:
            raise PanenException(f"Tanggal panen tidak valid: {tanggal_panen}")
        if tanggal > date.today():
            raise PanenException("Tanggal panen tidak boleh di masa depan")

        # 2. cari objek terkait lewat repo
        pohon = self.repo_pohon.ambil_berdasarkan_nomor(nomor_pohon)
        if pohon is None:
            raise PanenException(f"Pohon nomor {nomor_pohon} belum terdaftar")
        jenis = self.repo_jenis.ambil_berdasarkan_nama(nama_jenis)
        if jenis is None:
            raise PanenException(f"Jenis '{nama_jenis}' belum terdaftar")
        varietas = self.repo_varietas.ambil_berdasarkan_nama(nama_varietas, jenis)
        if varietas is None:
            raise PanenException(
                f"Varietas '{nama_varietas}' belum terdaftar untuk {jenis.get_nama_jenis()}")
        keterangan = self.repo_keterangan.ambil_berdasarkan_nama(nama_keterangan)
        if keterangan is None:
            raise PanenException(f"Keterangan '{nama_keterangan}' belum terdaftar")

        # 3. simpan dalam satu transaksi
        buah = Buah(pohon, varietas, bobot, keterangan, tanggal.isoformat())
        with self.conn:  # commit jika berhasil, rollback jika error
            self.repo_buah.simpan(buah)
        return buah
