import sqlite3
from typing import Optional

from pencatatan_kebun.models import JenisTanaman, KeteranganBuah, Pohon, Varietas
from pencatatan_kebun.repo.jenis_tanaman import RepoJenisTanaman
from pencatatan_kebun.repo.keterangan_buah import RepoKeteranganBuah
from pencatatan_kebun.repo.pohon import RepoPohon
from pencatatan_kebun.repo.varietas import RepoVarietas
from pencatatan_kebun.services.exception import DataMasihDipakaiException, DataSudahAdaException, DataTidakDitemukanException, NamaKosongException, NomorPohonTidakValidException


class MasterService:
    """Kelola data induk: jenis tanaman, varietas, pohon, dan keterangan buah.

    Semua fungsi yang mengubah data melempar ServiceException dengan pesan
    yang jelas jika input tidak valid, lalu commit dalam satu transaksi.

    Args:
        conn: Koneksi database dari buka_koneksi.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.repo_jenis = RepoJenisTanaman(conn)
        self.repo_varietas = RepoVarietas(conn)
        self.repo_pohon = RepoPohon(conn)
        self.repo_keterangan = RepoKeteranganBuah(conn)

    # ---- jenis tanaman ----
    def _cek_jenis(self, nama_jenis: str, id_jenis: Optional[str] = None) -> None:
        """Cek nama jenis sebelum tambah/ubah.

        Args:
            nama_jenis: Nama jenis yang dicek.
            id_jenis: Id jenis yang sedang diubah, khusu fungsi ubah.

        Raises:
            NamaKosongException: Nama kosong.
            DataSudahAdaException: Nama sudah dipakai jenis lain.
        """
        if nama_jenis is None or nama_jenis.strip() == "":
            raise NamaKosongException("Nama jenis", kolom="nama_jenis")
        ada = self.repo_jenis.read_by_name(nama_jenis)
        if ada is not None and ada.get_id_jenis() != id_jenis:
            raise DataSudahAdaException(nama_jenis, kolom="nama_jenis")


    def tambah_jenis(self, nama_jenis: str, deskripsi: str = "") -> JenisTanaman:
        """Tambah jenis tanaman baru.

        Args:
            nama_jenis: Nama jenis, mis. "Durian". Wajib diisi, unik tanpa
                membedakan huruf besar/kecil.
            deskripsi: Keterangan tambahan, boleh kosong.

        Returns:
            JenisTanaman yang tersimpan.

        Raises:
            NamaKosongException: Nama kosong.
            DataSudahAdaException: Nama sudah dipakai.
        """
        self._cek_jenis((nama_jenis or "").strip())

        jenis = JenisTanaman((nama_jenis or "").strip(), deskripsi)
        self.repo_jenis.create(jenis)
        self.conn.commit()
        return jenis


    def ubah_jenis(self, id_jenis: str, nama_jenis: str, deskripsi: str = "") -> JenisTanaman:
        """Ubah nama dan deskripsi jenis tanaman.

        Args:
            id_jenis: Id jenis yang diubah.
            nama_jenis: Nama baru. Wajib diisi, unik.
            deskripsi: Deskripsi baru.

        Returns:
            JenisTanaman setelah diubah.

        Raises:
            DataTidakDitemukanException: Jenis tidak ditemukan.
            NamaKosongException: Nama kosong.
            DataSudahAdaException: Nama sudah dipakai jenis lain.
        """
        if self.repo_jenis.read(id_jenis) is None:
            raise DataTidakDitemukanException(f"jenis tanaman dengan id {id_jenis}", kolom="id_jenis")
        self._cek_jenis((nama_jenis or "").strip(), id_jenis=id_jenis)

        jenis = JenisTanaman((nama_jenis or "").strip(), deskripsi, id_jenis=id_jenis)
        self.repo_jenis.update(jenis)
        self.conn.commit()
        return jenis
    

    def hapus_jenis(self, id_jenis: str) -> None:
        """Hapus jenis tanaman.

        Args:
            id_jenis: Id jenis yang dihapus.

        Raises:
            DataTidakDitemukanException: Jenis tidak ditemukan.
            DataMasihDipakaiException: Jenis masih punya varietas.
        """
        jenis = self.repo_jenis.read(id_jenis)
        if jenis is None:
            raise DataTidakDitemukanException(f"jenis tanaman dengan id {id_jenis}", kolom="id_jenis")
        if self.repo_jenis.is_jenis_used(id_jenis):
            raise DataMasihDipakaiException(f"jenis tanaman {jenis.get_nama_jenis()}", kolom="id_jenis")

        self.repo_jenis.delete(id_jenis)
        self.conn.commit()
        

    def daftar_jenis(self) -> list[JenisTanaman]:
        """Semua jenis tanaman.

        Returns:
            Daftar JenisTanaman, urut berdasarkan nama.
        """
        return self.repo_jenis.read_all()
    

    # ---- varietas ----
    def _cek_varietas(self, nama_varietas: str, jenis: JenisTanaman, id_varietas: Optional[str] = None) -> None:
        """Cek nama varietas sebelum tambah/ubah.

        Args:
            nama_varietas: Nama varietas yang dicek.
            jenis: JenisTanaman pemilik varietas.
            id_varietas: Id varietas yang sedang diubah, khusus fungsi ubah.
        
        Raises:
            NamaKosongException: Nama kosong.
            DataSudahAdaException: Nama sudah dipakai varietas lain di jenis ini.
            DataTidakDitemukanException: Jenis tidak ditemukan di database.
        """
        if self.repo_jenis.read(jenis.get_id_jenis()) is None:
            raise DataTidakDitemukanException(f"jenis tanaman {jenis.get_nama_jenis()}", kolom="id_jenis")
        if nama_varietas is None or nama_varietas.strip() == "":
            raise NamaKosongException("Nama varietas", kolom="nama_varietas")
        ada = self.repo_varietas.read_by_name(nama_varietas, jenis)
        if ada is not None and ada.get_id_varietas() != id_varietas:
            raise DataSudahAdaException(f"varietas {nama_varietas} di jenis {jenis.get_nama_jenis()}", kolom="nama_varietas")

    def tambah_varietas(self, jenis: JenisTanaman, nama_varietas: str,
                        deskripsi: str = "") -> Varietas:
        """Tambah varietas baru pada satu jenis tanaman.

        Args:
            jenis: Objek JenisTanaman pemilik varietas (dipilih dari dropdown).
            nama_varietas: Nama varietas, mis. "Musang King". Wajib diisi,
                unik di dalam jenis yang sama (boleh sama di jenis lain).
            deskripsi: Keterangan tambahan, boleh kosong.

        Returns:
            Varietas yang tersimpan.

        Raises:
            NamaKosongException: Nama kosong.
            DataSudahAdaException: Nama sudah ada di jenis tersebut.
            DataTidakDitemukanException: Jenis sudah tidak ada di database.
        """
        self._cek_varietas((nama_varietas or "").strip(), jenis)

        varietas = Varietas((nama_varietas or "").strip(), jenis, deskripsi)
        self.repo_varietas.create(varietas)
        self.conn.commit()
        return varietas

    def ubah_varietas(self, id_varietas: str, jenis: JenisTanaman, nama_varietas: str,
                      deskripsi: str = "") -> Varietas:
        """Ubah varietas, termasuk memindahkannya ke jenis lain.

        Args:
            id_varietas: Id varietas yang diubah.
            jenis: Objek JenisTanaman (baru atau tetap).
            nama_varietas: Nama baru. Wajib diisi, unik di dalam jenisnya.
            deskripsi: Deskripsi baru.

        Returns:
            Varietas setelah diubah.

        Raises:
            DataTidakDitemukanException: Varietas tidak ditemukan, atau jenis
                sudah tidak ada di database.
            NamaKosongException: Nama kosong.
            DataSudahAdaException: Nama sudah ada di jenis tujuan.
        """
        if self.repo_varietas.read(id_varietas) is None:
            raise DataTidakDitemukanException(f"varietas dengan id {id_varietas}", kolom="id_varietas")
        self._cek_varietas((nama_varietas or "").strip(), jenis, id_varietas=id_varietas)

        varietas = Varietas((nama_varietas or "").strip(), jenis, deskripsi, id_varietas=id_varietas)
        self.repo_varietas.update(varietas)
        self.conn.commit()
        return varietas

    def hapus_varietas(self, id_varietas: str) -> None:
        """Hapus varietas.

        Args:
            id_varietas: Id varietas yang dihapus.

        Raises:
            DataTidakDitemukanException: Varietas tidak ditemukan.
            DataMasihDipakaiException: Varietas sudah dipakai catatan buah.
        """
        varietas = self.repo_varietas.read(id_varietas)
        if varietas is None:
            raise DataTidakDitemukanException(f"varietas dengan id {id_varietas}", kolom="id_varietas")
        if self.repo_varietas.is_varietas_used(id_varietas):
            raise DataMasihDipakaiException(f"varietas {varietas.get_nama_varietas()}", kolom="id_varietas")

        self.repo_varietas.delete(id_varietas)
        self.conn.commit()

    def daftar_varietas(self, jenis: Optional[JenisTanaman] = None) -> list[Varietas]:
        """Daftar varietas.

        Args:
            jenis: Jika diisi, hanya varietas dari jenis ini (mis. untuk
                mengisi dropdown varietas setelah pengguna memilih jenis di
                form panen). Jika None, semua varietas.

        Returns:
            Daftar Varietas, urut berdasarkan jenis lalu nama.
        """
        return self.repo_varietas.read_by_jenis(jenis)

    # ---- pohon ----

    def _cek_pohon(self, nomor_pohon: int, id_pohon: Optional[str] = None) -> None:
        """Cek nomor pohon sebelum tambah/ubah.

        Args:
            nomor_pohon: Nomor pohon yang dicek.
            id_pohon: Id pohon yang sedang diubah, khusus fungsi ubah.

        Raises:
            NomorPohonTidakValidException: Nomor bukan bilangan bulat positif.
            DataSudahAdaException: Nomor sudah dipakai pohon lain.
        """
        if isinstance(nomor_pohon, bool) or not isinstance(nomor_pohon, int) or nomor_pohon <= 0:
            raise NomorPohonTidakValidException()
        ada = self.repo_pohon.read_by_number(nomor_pohon)
        if ada is not None and ada.get_id_pohon() != id_pohon:
            raise DataSudahAdaException(f"nomor pohon {nomor_pohon}", kolom="nomor_pohon")

    def tambah_pohon(self, nomor_pohon: int) -> Pohon:
        """Daftarkan pohon baru.

        Args:
            nomor_pohon: Nomor pohon di kebun. Bilangan bulat positif, unik.

        Returns:
            Pohon yang tersimpan.

        Raises:
            NomorPohonTidakValidException: Nomor bukan bilangan bulat positif.
            DataSudahAdaException: Nomor sudah dipakai.
        """
        self._cek_pohon(nomor_pohon)

        pohon = Pohon(nomor_pohon)
        self.repo_pohon.create(pohon)
        self.conn.commit()
        return pohon

    def ubah_pohon(self, id_pohon: str, nomor_pohon: int) -> Pohon:
        """Ganti nomor pohon.

        Args:
            id_pohon: Id pohon yang diubah.
            nomor_pohon: Nomor baru. Bilangan bulat positif, unik.

        Returns:
            Pohon setelah diubah.

        Raises:
            DataTidakDitemukanException: Pohon tidak ditemukan.
            NomorPohonTidakValidException: Nomor bukan bilangan bulat positif.
            DataSudahAdaException: Nomor sudah dipakai pohon lain.
        """
        if self.repo_pohon.read(id_pohon) is None:
            raise DataTidakDitemukanException(f"pohon dengan id {id_pohon}", kolom="id_pohon")
        self._cek_pohon(nomor_pohon, id_pohon=id_pohon)

        pohon = Pohon(nomor_pohon, id_pohon=id_pohon)
        self.repo_pohon.update(pohon)
        self.conn.commit()
        return pohon

    def hapus_pohon(self, id_pohon: str) -> None:
        """Hapus pohon.

        Args:
            id_pohon: Id pohon yang dihapus.

        Raises:
            DataTidakDitemukanException: Pohon tidak ditemukan.
            DataMasihDipakaiException: Pohon sudah punya catatan buah.
        """
        pohon = self.repo_pohon.read(id_pohon)
        if pohon is None:
            raise DataTidakDitemukanException(f"pohon dengan id {id_pohon}", kolom="id_pohon")
        if self.repo_pohon.is_pohon_used(id_pohon):
            raise DataMasihDipakaiException(f"pohon {pohon.get_nomor_pohon()}", kolom="id_pohon")

        self.repo_pohon.delete(id_pohon)
        self.conn.commit()

    def daftar_pohon(self) -> list[Pohon]:
        """Semua pohon.

        Returns:
            Daftar Pohon, urut berdasarkan nomor.
        """
        return self.repo_pohon.read_all()

    # ---- keterangan buah ----

    def _cek_keterangan(self, nama_keterangan: str, id_keterangan: Optional[str] = None) -> None:
        """Cek nama keterangan sebelum tambah/ubah.

        Args:
            nama_keterangan: Nama keterangan yang dicek.
            id_keterangan: Id keterangan yang sedang diubah, khusus fungsi ubah.
        
        Raises:
            NamaKosongException: Nama kosong.
            DataSudahAdaException: Nama sudah dipakai.
        """
        if nama_keterangan is None or nama_keterangan.strip() == "":
            raise NamaKosongException("Nama keterangan", kolom="nama_keterangan")
        ada = self.repo_keterangan.read_by_name(nama_keterangan)
        if ada is not None and ada.get_id_keterangan() != id_keterangan:
            raise DataSudahAdaException(f"keterangan buah {nama_keterangan}", kolom="nama_keterangan")

    def tambah_keterangan(self, nama_keterangan: str, deskripsi: str = "") -> KeteranganBuah:
        """Tambah keterangan kondisi buah, mis. "Baik" atau "Busuk".

        Args:
            nama_keterangan: Nama keterangan. Wajib diisi, unik tanpa
                membedakan huruf besar/kecil.
            deskripsi: Penjelasan tambahan, boleh kosong.

        Returns:
            KeteranganBuah yang tersimpan.

        Raises:
            NamaKosongException: Nama kosong.
            DataSudahAdaException: Nama sudah dipakai.
        """
        self._cek_keterangan((nama_keterangan or "").strip())

        keterangan = KeteranganBuah((nama_keterangan or "").strip(), deskripsi)
        self.repo_keterangan.create(keterangan)
        self.conn.commit()
        return keterangan

    def ubah_keterangan(self, id_keterangan: str, nama_keterangan: str,
                        deskripsi: str = "") -> KeteranganBuah:
        """Ubah nama dan deskripsi keterangan buah.

        Args:
            id_keterangan: Id keterangan yang diubah.
            nama_keterangan: Nama baru. Wajib diisi, unik.
            deskripsi: Deskripsi baru.

        Returns:
            KeteranganBuah setelah diubah.

        Raises:
            DataTidakDitemukanException: Keterangan tidak ditemukan.
            NamaKosongException: Nama kosong.
            DataSudahAdaException: Nama sudah dipakai keterangan lain.
        """
        if self.repo_keterangan.read(id_keterangan) is None:
            raise DataTidakDitemukanException(f"keterangan buah dengan id {id_keterangan}", kolom="id_keterangan")
        self._cek_keterangan((nama_keterangan or "").strip(), id_keterangan=id_keterangan)

        keterangan = KeteranganBuah((nama_keterangan or "").strip(), deskripsi, id_keterangan=id_keterangan)
        self.repo_keterangan.update(keterangan)
        self.conn.commit()
        return keterangan

    def hapus_keterangan(self, id_keterangan: str) -> None:
        """Hapus keterangan buah.

        Args:
            id_keterangan: Id keterangan yang dihapus.

        Raises:
            DataTidakDitemukanException: Keterangan tidak ditemukan.
            DataMasihDipakaiException: Keterangan sudah dipakai catatan buah.
        """
        keterangan = self.repo_keterangan.read(id_keterangan)
        if keterangan is None:
            raise DataTidakDitemukanException(f"keterangan buah dengan id {id_keterangan}", kolom="id_keterangan")
        if self.repo_keterangan.is_keterangan_used(id_keterangan):
            raise DataMasihDipakaiException(f"keterangan buah {keterangan.get_nama_keterangan()}", kolom="id_keterangan")
        
        self.repo_keterangan.delete(id_keterangan)
        self.conn.commit()

    def daftar_keterangan(self) -> list[KeteranganBuah]:
        """Semua keterangan buah.

        Returns:
            Daftar KeteranganBuah, urut berdasarkan nama.
        """
        return self.repo_keterangan.read_all()
