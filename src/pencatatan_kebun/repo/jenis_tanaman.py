import sqlite3
from typing import Optional

from pencatatan_kebun.models import JenisTanaman


class RepoJenisTanaman:
    """Akses tabel jenis_tanaman.

    Koneksi dikirim dari luar (dari buka_koneksi, atau ":memory:" di tes).
    Repo tidak memanggil commit(): transaksi diurus service. Pelanggaran aturan
    skema (unik, foreign key, CHECK, trigger) dibiarkan naik sebagai
    sqlite3.IntegrityError untuk diterjemahkan service.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, jenis_tanaman: JenisTanaman) -> None:
        self.conn.execute(
            "INSERT INTO jenis_tanaman (id_jenis, nama_jenis, deskripsi) VALUES (?, ?, ?)",
            (jenis_tanaman.get_id_jenis(), jenis_tanaman.get_nama_jenis(), jenis_tanaman.get_deskripsi()))

    def read(self, id_jenis: str) -> Optional[JenisTanaman]:
        """Jenis dengan id tersebut, atau None jika tidak ada."""
        baris = self.conn.execute(
            "SELECT id_jenis, nama_jenis, deskripsi FROM jenis_tanaman WHERE id_jenis = ?",
            (id_jenis,)).fetchone()
        if baris is None:
            return None
        
        return JenisTanaman(
            baris["nama_jenis"],
            baris["deskripsi"],
            id_jenis=baris["id_jenis"]
        )

    def read_all(self) -> list[JenisTanaman]:
        """Semua jenis, urut berdasarkan nama (tanpa membedakan huruf besar/kecil)."""
        baris_list = self.conn.execute(
            "SELECT id_jenis, nama_jenis, deskripsi FROM jenis_tanaman ORDER BY nama_jenis").fetchall()
        
        return [
            JenisTanaman(
                baris["nama_jenis"],
                baris["deskripsi"],
                id_jenis=baris["id_jenis"]
            )
            for baris in baris_list
        ]

    def read_by_name(self, nama_jenis: str) -> Optional[JenisTanaman]:
        """Jenis dengan nama tersebut, atau None. Tidak membedakan huruf besar/kecil."""
        baris = self.conn.execute(
            "SELECT id_jenis, nama_jenis, deskripsi FROM jenis_tanaman WHERE nama_jenis = ?",
            (nama_jenis,)).fetchone()
        if baris is None:
            return None
        
        return JenisTanaman(
            baris["nama_jenis"],
            baris["deskripsi"],
            id_jenis=baris["id_jenis"]
        )

    def read_by_names(self, nama_jenis: list[str]) -> list[JenisTanaman]:
        """Jenis yang namanya ada di daftar, urut berdasarkan nama.

        Tidak membedakan huruf besar/kecil. Nama yang tidak ditemukan dilewati;
        daftar kosong menghasilkan [].
        """
        baris_list = self.conn.execute(
            "SELECT id_jenis, nama_jenis, deskripsi FROM jenis_tanaman WHERE nama_jenis IN ({}) ORDER BY nama_jenis".format(",".join("?" * len(nama_jenis))),
            tuple(nama_jenis)).fetchall()

        return [
            JenisTanaman(
                baris["nama_jenis"],
                baris["deskripsi"],
                id_jenis=baris["id_jenis"]
            )
            for baris in baris_list
        ]

    def delete(self, id_jenis: str) -> None:
        """Hapus jenis. Tidak error jika id tidak ada.

        Ditolak (IntegrityError) jika jenis masih punya varietas.
        """
        self.conn.execute(
            "DELETE FROM jenis_tanaman WHERE id_jenis = ?",
            (id_jenis,))

    def update(self, jenis_tanaman: JenisTanaman) -> None:
        """Simpan perubahan nama dan deskripsi. Tidak error jika id tidak ada."""
        self.conn.execute(
            "UPDATE jenis_tanaman SET nama_jenis = ?, deskripsi = ? WHERE id_jenis = ?",
            (jenis_tanaman.get_nama_jenis(), jenis_tanaman.get_deskripsi(), jenis_tanaman.get_id_jenis()))
        