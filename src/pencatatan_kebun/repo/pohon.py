import sqlite3

from pencatatan_kebun.models import Pohon, Varietas
from pencatatan_kebun.repo.varietas import RepoVarietas


class RepoPohon:
    """Akses tabel pohon. Satu pohon punya satu varietas; nomor pohon hanya
    unik di dalam varietasnya.

    Objek Varietas (beserta jenisnya) di setiap Pohon ikut dimuat lewat
    RepoVarietas.

    Repo tidak memanggil commit(): transaksi diurus service. Pelanggaran aturan
    skema (unik, foreign key, CHECK, trigger) dibiarkan naik sebagai
    sqlite3.IntegrityError untuk diterjemahkan service.

    Args:
        conn: Koneksi database dari luar (dari buka_koneksi, atau ":memory:"
            di tes).
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, pohon: Pohon) -> None:
        """Simpan pohon baru.

        Args:
            pohon: Pohon yang disimpan.

        Raises:
            sqlite3.IntegrityError: Nomor sudah dipakai di varietas yang sama,
                varietas tidak ada di database, atau data melanggar CHECK di
                skema.
        """
        self.conn.execute(
            "INSERT INTO pohon (id_pohon, id_varietas, nomor_pohon) VALUES (?, ?, ?)",
            (pohon.get_id_pohon(), pohon.get_varietas().get_id_varietas(), pohon.get_nomor_pohon()))

    def read(self, id_pohon: str) -> Pohon | None:
        """Ambil satu pohon berdasarkan id.

        Args:
            id_pohon: Id pohon yang dicari.

        Returns:
            Pohon beserta varietasnya, atau None jika tidak ada.
        """
        baris = self.conn.execute(
            "SELECT id_pohon, id_varietas, nomor_pohon FROM pohon WHERE id_pohon = ?",
            (id_pohon,)).fetchone()
        if baris is None:
            return None

        return Pohon(
            baris["nomor_pohon"],
            RepoVarietas(self.conn).read(baris["id_varietas"]),
            id_pohon=baris["id_pohon"]
        )

    def read_all(self) -> list[Pohon]:
        """Ambil semua pohon.

        Returns:
            Daftar Pohon, urut berdasarkan nama jenis, nama varietas, lalu nomor.
        """
        baris_list = self.conn.execute(
            "SELECT p.id_pohon, p.id_varietas, p.nomor_pohon FROM pohon p "
            "JOIN varietas v ON v.id_varietas = p.id_varietas "
            "JOIN jenis_tanaman j ON j.id_jenis = v.id_jenis "
            "ORDER BY j.nama_jenis, v.nama_varietas, p.nomor_pohon").fetchall()

        return [
            Pohon(
                baris["nomor_pohon"],
                RepoVarietas(self.conn).read(baris["id_varietas"]),
                id_pohon=baris["id_pohon"]
            )
            for baris in baris_list
        ]

    def read_by_varietas(self, varietas: Varietas | None) -> list[Pohon]:
        """Ambil pohon di satu varietas, mis. untuk dropdown pohon setelah
        pengguna memilih varietas.

        Args:
            varietas: Varietas pohon. Jika None, ambil semua pohon.

        Returns:
            Daftar Pohon, urut berdasarkan nomor. Varietas tidak ada di
            database menghasilkan [].
        """
        if varietas is None:
            return self.read_all()
        baris_list = self.conn.execute(
            "SELECT id_pohon, id_varietas, nomor_pohon FROM pohon WHERE id_varietas = ? ORDER BY nomor_pohon",
            (varietas.get_id_varietas(),)).fetchall()

        return [
            Pohon(
                baris["nomor_pohon"],
                RepoVarietas(self.conn).read(baris["id_varietas"]),
                id_pohon=baris["id_pohon"]
            )
            for baris in baris_list
        ]

    def read_by_number(self, nomor_pohon: int, varietas: Varietas) -> Pohon | None:
        """Ambil satu pohon berdasarkan nomor di dalam satu varietas.

        Args:
            nomor_pohon: Nomor pohon yang dicari.
            varietas: Varietas pohon. Wajib diisi karena nomor pohon hanya
                unik per varietas (mis. Bawor 1 dan Montong 1).

        Returns:
            Pohon, atau None jika tidak ada.
        """
        baris = self.conn.execute(
            "SELECT id_pohon, id_varietas, nomor_pohon FROM pohon WHERE nomor_pohon = ? AND id_varietas = ?",
            (nomor_pohon, varietas.get_id_varietas())).fetchone()
        if baris is None:
            return None

        return Pohon(
            baris["nomor_pohon"],
            RepoVarietas(self.conn).read(baris["id_varietas"]),
            id_pohon=baris["id_pohon"]
        )

    def read_by_numbers(self, nomor_pohon: list[int], varietas: Varietas) -> list[Pohon]:
        """Ambil pohon di satu varietas yang nomornya ada di daftar.

        Args:
            nomor_pohon: Daftar nomor pohon yang dicari.
            varietas: Varietas pohon.

        Returns:
            Daftar Pohon, urut berdasarkan nomor. Nomor yang tidak ditemukan
            dilewati; daftar kosong menghasilkan [].
        """
        baris_list = self.conn.execute(
            "SELECT id_pohon, id_varietas, nomor_pohon FROM pohon "
            "WHERE id_varietas = ? AND nomor_pohon IN ({}) ORDER BY nomor_pohon".format(",".join("?" * len(nomor_pohon))),
            (varietas.get_id_varietas(), *nomor_pohon)).fetchall()

        return [
            Pohon(
                baris["nomor_pohon"],
                RepoVarietas(self.conn).read(baris["id_varietas"]),
                id_pohon=baris["id_pohon"]
            )
            for baris in baris_list
        ]

    def is_pohon_used(self, id_pohon: str) -> bool:
        """Cek apakah pohon sudah dipakai catatan buah atau stok pohon.

        Args:
            id_pohon: Id pohon yang dicek.

        Returns:
            True jika sudah dipakai, False jika belum.
        """
        baris = self.conn.execute(
            "SELECT EXISTS (SELECT 1 FROM buah WHERE id_pohon = ?) "
            "OR EXISTS (SELECT 1 FROM stok_pohon WHERE id_pohon = ?) AS dipakai",
            (id_pohon, id_pohon)).fetchone()
        return bool(baris["dipakai"])

    def delete(self, id_pohon: str) -> None:
        """Hapus pohon. Tidak error jika id tidak ada.

        Args:
            id_pohon: Id pohon yang dihapus.

        Raises:
            sqlite3.IntegrityError: Pohon sudah punya catatan buah atau stok.
        """
        self.conn.execute(
            "DELETE FROM pohon WHERE id_pohon = ?",
            (id_pohon,))

    def update(self, pohon: Pohon) -> None:
        """Simpan perubahan nomor dan varietas pohon. Tidak error jika id tidak ada.

        Args:
            pohon: Pohon dengan data baru; dicocokkan lewat id_pohon.

        Raises:
            sqlite3.IntegrityError: Nomor sudah dipakai pohon lain di varietas
                yang sama, varietas tidak ada di database, atau data melanggar
                CHECK di skema.
        """
        self.conn.execute(
            "UPDATE pohon SET id_varietas = ?, nomor_pohon = ? WHERE id_pohon = ?",
            (pohon.get_varietas().get_id_varietas(), pohon.get_nomor_pohon(), pohon.get_id_pohon()))
