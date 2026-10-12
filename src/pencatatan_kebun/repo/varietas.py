import sqlite3

from pencatatan_kebun.models import JenisTanaman, Varietas
from pencatatan_kebun.repo.jenis_tanaman import RepoJenisTanaman


class RepoVarietas:
    """Akses tabel varietas.

    Objek JenisTanaman di setiap Varietas ikut dimuat lewat RepoJenisTanaman.

    Repo tidak memanggil commit(): transaksi diurus service. Pelanggaran aturan
    skema (unik, foreign key, CHECK, trigger) dibiarkan naik sebagai
    sqlite3.IntegrityError untuk diterjemahkan service.

    Args:
        conn: Koneksi database dari luar (dari buka_koneksi, atau ":memory:"
            di tes).
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, varietas: Varietas) -> None:
        """Simpan varietas baru.

        Args:
            varietas: Varietas yang disimpan.

        Raises:
            sqlite3.IntegrityError: Nama sudah ada di jenis yang sama, jenis
                tidak ada di database, atau data melanggar CHECK di skema.
        """
        self.conn.execute(
            "INSERT INTO varietas (id_varietas, nama_varietas, id_jenis, deskripsi) VALUES (?, ?, ?, ?)",
            (varietas.get_id_varietas(), varietas.get_nama_varietas(), varietas.get_jenis().get_id_jenis(), varietas.get_deskripsi()))

    def read(self, id_varietas: str) -> Varietas | None:
        """Ambil satu varietas berdasarkan id.

        Args:
            id_varietas: Id varietas yang dicari.

        Returns:
            Varietas beserta jenisnya, atau None jika tidak ada.
        """
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
        """Ambil semua varietas.

        Returns:
            Daftar Varietas, urut berdasarkan nama jenis lalu nama varietas.
        """
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

    def read_by_name(self, nama_varietas: str, jenis: JenisTanaman) -> Varietas | None:
        """Ambil satu varietas berdasarkan nama di dalam satu jenis.

        Tidak membedakan huruf besar/kecil.

        Args:
            nama_varietas: Nama varietas yang dicari.
            jenis: Jenis pemilik varietas. Wajib diisi karena nama varietas
                hanya unik per jenis (mis. "Lokal" bisa ada di Durian dan Mangga).

        Returns:
            Varietas, atau None jika tidak ada.
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
        """Ambil varietas dari semua jenis yang namanya ada di daftar.

        Tidak membedakan huruf besar/kecil.

        Args:
            nama_varietas: Daftar nama varietas yang dicari.

        Returns:
            Daftar Varietas, urut berdasarkan nama jenis lalu nama varietas.
            Nama yang sama di beberapa jenis ikut semua; daftar kosong
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

    def read_by_jenis(self, jenis: JenisTanaman | None) -> list[Varietas]:
        """Ambil varietas di satu jenis.
        
        Args:
            jenis: Jenis pemilik varietas. Jika None, ambil semua varietas.
            
        Returns:
            Daftar Varietas, urut berdasarkan nama varietas. Jenis di setiap
            Varietas ikut dimuat. Jenis tidak ada di database menghasilkan [].
        """
        if jenis is None:
            return self.read_all()
        baris_list = self.conn.execute(
            "SELECT id_varietas, nama_varietas, id_jenis, deskripsi FROM varietas WHERE id_jenis = ? ORDER BY nama_varietas",
            (jenis.get_id_jenis(),)).fetchall()

        return [
            Varietas(
                baris["nama_varietas"],
                RepoJenisTanaman(self.conn).read(baris["id_jenis"]),
                baris["deskripsi"],
                id_varietas=baris["id_varietas"]
            )
            for baris in baris_list
        ]

    def is_varietas_used(self, id_varietas: str) -> bool:
        """Cek apakah varietas sudah dipakai pohon.

        Args:
            id_varietas: Id varietas yang dicek.

        Returns:
            True jika ada pohon yang memakai varietas ini, False jika tidak.
        """
        baris = self.conn.execute(
            "SELECT COUNT(*) AS jumlah FROM pohon WHERE id_varietas = ?",
            (id_varietas,)).fetchone()
        return baris["jumlah"] > 0

    def delete(self, id_varietas: str) -> None:
        """Hapus varietas. Tidak error jika id tidak ada.

        Args:
            id_varietas: Id varietas yang dihapus.

        Raises:
            sqlite3.IntegrityError: Varietas masih dipakai pohon.
        """
        self.conn.execute(
            "DELETE FROM varietas WHERE id_varietas = ?",
            (id_varietas,))

    def update(self, varietas: Varietas) -> None:
        """Simpan perubahan nama, jenis, dan deskripsi (varietas boleh pindah jenis).

        Tidak error jika id tidak ada.

        Args:
            varietas: Varietas dengan data baru; dicocokkan lewat id_varietas.

        Raises:
            sqlite3.IntegrityError: Nama sudah ada di jenis tujuan, atau jenis
                tidak ada di database.
        """
        self.conn.execute(
            "UPDATE varietas SET nama_varietas = ?, id_jenis = ?, deskripsi = ? WHERE id_varietas = ?",
            (varietas.get_nama_varietas(), varietas.get_jenis().get_id_jenis(), varietas.get_deskripsi(), varietas.get_id_varietas()))
        