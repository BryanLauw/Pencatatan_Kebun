import sqlite3

from pencatatan_kebun.models import Buah
from pencatatan_kebun.repo.keterangan_buah import RepoKeteranganBuah
from pencatatan_kebun.repo.pohon import RepoPohon


class RepoBuah:
    """Akses tabel buah (catatan hasil panen).

    Objek Pohon (beserta varietas dan jenisnya) dan KeteranganBuah di setiap
    Buah ikut dimuat lewat repo masing-masing.

    Repo tidak memanggil commit(): transaksi diurus service. Pelanggaran aturan
    skema (unik, foreign key, CHECK, trigger) dibiarkan naik sebagai
    sqlite3.IntegrityError untuk diterjemahkan service.

    Args:
        conn: Koneksi database dari luar (dari buka_koneksi, atau ":memory:"
            di tes).
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, buah: Buah) -> None:
        """Simpan catatan buah baru.

        Args:
            buah: Buah yang disimpan.

        Raises:
            sqlite3.IntegrityError: Pohon/keterangan tidak ada di
                database, atau data melanggar CHECK di skema.
        """
        self.conn.execute(
            "INSERT INTO buah (id_buah, id_pohon, tanggal_panen, id_keterangan, bobot) VALUES (?, ?, ?, ?, ?)",
            (buah.get_id_buah(), buah.get_pohon().get_id_pohon(), buah.get_tanggal_panen(), buah.get_keterangan().get_id_keterangan(), buah.get_bobot()))

    def read(self, id_buah: str) -> Buah | None:
        """Ambil satu buah berdasarkan id.

        Args:
            id_buah: Id buah yang dicari.

        Returns:
            Buah beserta objek relasinya, atau None jika tidak ada.
        """
        baris = self.conn.execute(
            "SELECT id_buah, id_pohon, tanggal_panen, id_keterangan, bobot FROM buah WHERE id_buah = ?",
            (id_buah,)).fetchone()
        if baris is None:
            return None
        
        pohon = RepoPohon(self.conn).read(baris["id_pohon"])
        keterangan_buah = RepoKeteranganBuah(self.conn).read(baris["id_keterangan"])

        return Buah(
            pohon,
            baris["bobot"],
            keterangan_buah,
            baris["tanggal_panen"],
            id_buah=baris["id_buah"]
        )

    def read_all(self) -> list[Buah]:
        """Ambil semua buah.

        Returns:
            Daftar Buah, urut berdasarkan tanggal panen lalu nomor pohon.
        """
        baris_list = self.conn.execute(
            "SELECT b.id_buah, b.id_pohon, b.tanggal_panen, b.id_keterangan, b.bobot FROM buah b "
            "JOIN pohon p ON p.id_pohon = b.id_pohon "
            "ORDER BY b.tanggal_panen, p.nomor_pohon").fetchall()
        
        return [
            Buah(
                RepoPohon(self.conn).read(baris["id_pohon"]),
                baris["bobot"],
                RepoKeteranganBuah(self.conn).read(baris["id_keterangan"]),
                baris["tanggal_panen"],
                id_buah=baris["id_buah"]
            )
            for baris in baris_list
        ]

    def read_by_harvest_date(self, tanggal_panen: str) -> list[Buah]:
        """Ambil buah yang dipanen pada satu tanggal.

        Args:
            tanggal_panen: Tanggal format YYYY-MM-DD.

        Returns:
            Daftar Buah, urut berdasarkan nomor pohon.
        """
        baris_list = self.conn.execute(
            "SELECT b.id_buah, b.id_pohon, b.tanggal_panen, b.id_keterangan, b.bobot FROM buah b "
            "JOIN pohon p ON p.id_pohon = b.id_pohon "
            "WHERE b.tanggal_panen = ? ORDER BY p.nomor_pohon",
            (tanggal_panen,)).fetchall()
        
        return [
            Buah(
                RepoPohon(self.conn).read(baris["id_pohon"]),
                baris["bobot"],
                RepoKeteranganBuah(self.conn).read(baris["id_keterangan"]),
                baris["tanggal_panen"],
                id_buah=baris["id_buah"]
            )
            for baris in baris_list
        ]

    def read_by_harvest_dates(self, tanggal_panen: list[str]) -> list[Buah]:
        """Ambil buah yang dipanen pada salah satu tanggal di daftar.

        Args:
            tanggal_panen: Daftar tanggal format YYYY-MM-DD.

        Returns:
            Daftar Buah, urut berdasarkan tanggal panen lalu nomor pohon.
            Daftar tanggal kosong menghasilkan [].
        """
        baris_list = self.conn.execute(
            "SELECT b.id_buah, b.id_pohon, b.tanggal_panen, b.id_keterangan, b.bobot FROM buah b "
            "JOIN pohon p ON p.id_pohon = b.id_pohon "
            "WHERE b.tanggal_panen IN ({}) ORDER BY b.tanggal_panen, p.nomor_pohon".format(",".join("?" * len(tanggal_panen))),
            tuple(tanggal_panen)).fetchall()

        return [
            Buah(
                RepoPohon(self.conn).read(baris["id_pohon"]),
                baris["bobot"],
                RepoKeteranganBuah(self.conn).read(baris["id_keterangan"]),
                baris["tanggal_panen"],
                id_buah=baris["id_buah"]
            )
            for baris in baris_list
        ]

    def read_by_harvest_date_range(self, mulai: str, selesai: str) -> list[Buah]:
        """Ambil buah yang dipanen di antara dua tanggal (inklusif).

        Args:
            mulai: Tanggal mulai format YYYY-MM-DD.
            selesai: Tanggal selesai format YYYY-MM-DD.

        Returns:
            Daftar Buah, urut berdasarkan tanggal panen lalu nomor pohon.
        """
        baris_list = self.conn.execute(
            "SELECT b.id_buah, b.id_pohon, b.tanggal_panen, b.id_keterangan, b.bobot FROM buah b "
            "JOIN pohon p ON p.id_pohon = b.id_pohon "
            "WHERE b.tanggal_panen BETWEEN ? AND ? ORDER BY b.tanggal_panen, p.nomor_pohon",
            (mulai, selesai)).fetchall()

        return [
            Buah(
                RepoPohon(self.conn).read(baris["id_pohon"]),
                baris["bobot"],
                RepoKeteranganBuah(self.conn).read(baris["id_keterangan"]),
                baris["tanggal_panen"],
                id_buah=baris["id_buah"]
            )
            for baris in baris_list
        ]

    def count_by_pohon_date_range(self, id_pohon: str, mulai: str, selesai: str) -> int:
        """Hitung buah satu pohon yang dipanen di antara dua tanggal (inklusif).

        Semua keterangan ikut dihitung (termasuk buah gugur), mis. untuk
        menghitung sisa buah di pohon pada satu periode.

        Args:
            id_pohon: Id pohon.
            mulai: Tanggal mulai format YYYY-MM-DD.
            selesai: Tanggal selesai format YYYY-MM-DD.

        Returns:
            Jumlah catatan buah, 0 jika tidak ada.
        """
        baris = self.conn.execute(
            "SELECT COUNT(*) AS jumlah FROM buah "
            "WHERE id_pohon = ? AND tanggal_panen BETWEEN ? AND ?",
            (id_pohon, mulai, selesai)).fetchone()
        return baris["jumlah"]

    def delete(self, id_buah: str) -> None:
        """Hapus satu catatan buah. Tidak error jika id tidak ada.

        Args:
            id_buah: Id buah yang dihapus.
        """
        self.conn.execute(
            "DELETE FROM buah WHERE id_buah = ?",
            (id_buah,))

    def update(self, buah: Buah) -> None:
        """Simpan perubahan semua kolom buah. Tidak error jika id tidak ada.

        Args:
            buah: Buah dengan data baru; dicocokkan lewat id_buah.

        Raises:
            sqlite3.IntegrityError: Pohon/keterangan tidak ada di
                database, atau data melanggar CHECK di skema.
        """
        self.conn.execute(
            "UPDATE buah SET id_pohon = ?, tanggal_panen = ?, id_keterangan = ?, bobot = ? WHERE id_buah = ?",
            (buah.get_pohon().get_id_pohon(), buah.get_tanggal_panen(), buah.get_keterangan().get_id_keterangan(), buah.get_bobot(), buah.get_id_buah()))
