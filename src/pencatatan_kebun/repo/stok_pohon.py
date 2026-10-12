import sqlite3

from pencatatan_kebun.models import StokPohon
from pencatatan_kebun.repo.periode_panen import RepoPeriodePanen
from pencatatan_kebun.repo.pohon import RepoPohon


class RepoStokPohon:
    """Akses tabel stok_pohon (jumlah buah per pohon per periode).

    Satu baris dikenali dari pasangan (id_pohon, id_periode). Objek Pohon
    (beserta varietas dan jenisnya) dan PeriodePanen di setiap StokPohon ikut
    dimuat lewat repo masing-masing.

    Repo tidak memanggil commit(): transaksi diurus service. Pelanggaran aturan
    skema (unik, foreign key, CHECK, trigger) dibiarkan naik sebagai
    sqlite3.IntegrityError untuk diterjemahkan service.

    Args:
        conn: Koneksi database dari luar (dari buka_koneksi, atau ":memory:"
            di tes).
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, stok: StokPohon) -> None:
        """Simpan stok baru.

        Args:
            stok: StokPohon yang disimpan.

        Raises:
            sqlite3.IntegrityError: Pohon sudah punya stok di periode ini,
                pohon/periode tidak ada di database, atau data melanggar CHECK
                di skema.
        """
        self.conn.execute(
            "INSERT INTO stok_pohon (id_pohon, id_periode, jumlah_buah, tanggal_hitung) VALUES (?, ?, ?, ?)",
            (stok.get_pohon().get_id_pohon(), stok.get_periode().get_id_periode(), stok.get_jumlah_buah(), stok.get_tanggal_hitung()))

    def read(self, id_pohon: str, id_periode: str) -> StokPohon | None:
        """Ambil stok satu pohon di satu periode.

        Args:
            id_pohon: Id pohon.
            id_periode: Id periode.

        Returns:
            StokPohon beserta objek relasinya, atau None jika tidak ada.
        """
        baris = self.conn.execute(
            "SELECT id_pohon, id_periode, jumlah_buah, tanggal_hitung FROM stok_pohon "
            "WHERE id_pohon = ? AND id_periode = ?",
            (id_pohon, id_periode)).fetchone()
        if baris is None:
            return None

        return StokPohon(
            RepoPohon(self.conn).read(baris["id_pohon"]),
            RepoPeriodePanen(self.conn).read(baris["id_periode"]),
            baris["jumlah_buah"],
            baris["tanggal_hitung"]
        )

    def read_by_periode(self, id_periode: str) -> list[StokPohon]:
        """Ambil stok semua pohon di satu periode.

        Args:
            id_periode: Id periode.

        Returns:
            Daftar StokPohon, urut berdasarkan nama jenis, nama varietas, lalu
            nomor pohon. Periode tanpa stok menghasilkan [].
        """
        baris_list = self.conn.execute(
            "SELECT s.id_pohon, s.id_periode, s.jumlah_buah, s.tanggal_hitung FROM stok_pohon s "
            "JOIN pohon p ON p.id_pohon = s.id_pohon "
            "JOIN varietas v ON v.id_varietas = p.id_varietas "
            "JOIN jenis_tanaman j ON j.id_jenis = v.id_jenis "
            "WHERE s.id_periode = ? "
            "ORDER BY j.nama_jenis, v.nama_varietas, p.nomor_pohon",
            (id_periode,)).fetchall()

        return [
            StokPohon(
                RepoPohon(self.conn).read(baris["id_pohon"]),
                RepoPeriodePanen(self.conn).read(baris["id_periode"]),
                baris["jumlah_buah"],
                baris["tanggal_hitung"]
            )
            for baris in baris_list
        ]

    def delete(self, id_pohon: str, id_periode: str) -> None:
        """Hapus stok satu pohon di satu periode. Tidak error jika tidak ada.

        Args:
            id_pohon: Id pohon.
            id_periode: Id periode.
        """
        self.conn.execute(
            "DELETE FROM stok_pohon WHERE id_pohon = ? AND id_periode = ?",
            (id_pohon, id_periode))

    def update(self, stok: StokPohon) -> None:
        """Simpan perubahan jumlah buah dan tanggal hitung. Tidak error jika
        stok tidak ada.

        Pohon dan periode tidak bisa diubah karena menjadi kunci; untuk
        memindahkan stok, hapus lalu buat baru.

        Args:
            stok: StokPohon dengan data baru; dicocokkan lewat pohon dan periode.

        Raises:
            sqlite3.IntegrityError: Data melanggar CHECK di skema.
        """
        self.conn.execute(
            "UPDATE stok_pohon SET jumlah_buah = ?, tanggal_hitung = ? WHERE id_pohon = ? AND id_periode = ?",
            (stok.get_jumlah_buah(), stok.get_tanggal_hitung(), stok.get_pohon().get_id_pohon(), stok.get_periode().get_id_periode()))
