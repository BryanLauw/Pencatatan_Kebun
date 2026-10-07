import sqlite3
from typing import Optional

from pencatatan_kebun.models import JenisTanaman, Varietas
from pencatatan_kebun.repo.jenis_tanaman import RepoJenisTanaman


class RepoVarietas:
    """Akses tabel varietas.

    Objek JenisTanaman di setiap Varietas ikut dimuat lewat RepoJenisTanaman.

    Koneksi dikirim dari luar (dari buka_koneksi, atau ":memory:" di tes).
    Repo tidak memanggil commit(): transaksi diurus service. Pelanggaran aturan
    skema (unik, foreign key, CHECK, trigger) dibiarkan naik sebagai
    sqlite3.IntegrityError untuk diterjemahkan service.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, varietas: Varietas) -> None:
        self.conn.execute(
            "INSERT INTO varietas (id_varietas, nama_varietas, id_jenis, deskripsi) VALUES (?, ?, ?, ?)",
            (varietas.get_id_varietas(), varietas.get_nama_varietas(), varietas.get_jenis().get_id_jenis(), varietas.get_deskripsi()))

    def read(self, id_varietas: str) -> Optional[Varietas]:
        """Varietas dengan id tersebut (beserta jenisnya), atau None jika tidak ada."""
        baris = self.conn.execute(
            "SELECT id_varietas, nama_varietas, id_jenis, deskripsi FROM varietas WHERE id_varietas = ?",
            (id_varietas,)).fetchone()
        if baris is None:
            return None
        
        jenis_tanaman = RepoJenisTanaman(self.conn).read(baris["id_jenis"])
        return Varietas(
            baris["nama_varietas"],
            jenis_tanaman,
            baris["deskripsi"],
            id_varietas=baris["id_varietas"]
        )

    def read_all(self) -> list[Varietas]:
        """Semua varietas, urut berdasarkan nama jenis lalu nama varietas."""
        baris_list = self.conn.execute(
            "SELECT v.id_varietas, v.nama_varietas, v.id_jenis, v.deskripsi FROM varietas v "
            "JOIN jenis_tanaman j ON j.id_jenis = v.id_jenis "
            "ORDER BY j.nama_jenis, v.nama_varietas").fetchall()
        
        return [
            Varietas(
                baris["nama_varietas"],
                RepoJenisTanaman(self.conn).read(baris["id_jenis"]),
                baris["deskripsi"],
                id_varietas=baris["id_varietas"]
            )
            for baris in baris_list
        ]

    def read_by_name(self, nama_varietas: str, jenis: JenisTanaman) -> Optional[Varietas]:
        """Varietas dengan nama tersebut di dalam satu jenis, atau None.

        Nama varietas hanya unik per jenis (mis. "Lokal" bisa ada di Durian dan
        Mangga), jadi jenis wajib diisi. Tidak membedakan huruf besar/kecil.
        """
        baris = self.conn.execute(
            "SELECT id_varietas, nama_varietas, id_jenis, deskripsi FROM varietas WHERE nama_varietas = ? AND id_jenis = ?",
            (nama_varietas, jenis.get_id_jenis())).fetchone()
        if baris is None:
            return None
        
        jenis_tanaman = RepoJenisTanaman(self.conn).read(baris["id_jenis"])
        return Varietas(
            baris["nama_varietas"],
            jenis_tanaman,
            baris["deskripsi"],
            id_varietas=baris["id_varietas"]
        )

    def read_by_names(self, nama_varietas: list[str]) -> list[Varietas]:
        """Varietas dari semua jenis yang namanya ada di daftar.

        Nama yang sama di beberapa jenis ikut semua. Urut berdasarkan nama jenis
        lalu nama varietas. Tidak membedakan huruf besar/kecil; daftar kosong
        menghasilkan [].
        """
        baris_list = self.conn.execute(
            "SELECT v.id_varietas, v.nama_varietas, v.id_jenis, v.deskripsi FROM varietas v "
            "JOIN jenis_tanaman j ON j.id_jenis = v.id_jenis "
            "WHERE v.nama_varietas IN ({}) ORDER BY j.nama_jenis, v.nama_varietas".format(",".join("?" * len(nama_varietas))),
            tuple(nama_varietas)).fetchall()

        return [
            Varietas(
                baris["nama_varietas"],
                RepoJenisTanaman(self.conn).read(baris["id_jenis"]),
                baris["deskripsi"],
                id_varietas=baris["id_varietas"]
            )
            for baris in baris_list
        ]

    def delete(self, id_varietas: str) -> None:
        """Hapus varietas. Tidak error jika id tidak ada.

        Ditolak (IntegrityError) jika masih dipakai catatan buah.
        """
        self.conn.execute(
            "DELETE FROM varietas WHERE id_varietas = ?",
            (id_varietas,))

    def update(self, varietas: Varietas) -> None:
        """Simpan perubahan nama, jenis, dan deskripsi (varietas boleh pindah jenis).

        Tidak error jika id tidak ada. Ditolak (IntegrityError) jika nama sudah
        ada di jenis tujuan.
        """
        self.conn.execute(
            "UPDATE varietas SET nama_varietas = ?, id_jenis = ?, deskripsi = ? WHERE id_varietas = ?",
            (varietas.get_nama_varietas(), varietas.get_jenis().get_id_jenis(), varietas.get_deskripsi(), varietas.get_id_varietas()))
        