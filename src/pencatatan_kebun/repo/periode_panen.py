import sqlite3

from pencatatan_kebun.models import PeriodePanen


class RepoPeriodePanen:
    """Akses tabel periode_panen.

    Trigger di skema menolak periode yang tumpang tindih dan otomatis menutup
    periode aktif saat periode baru dibuat.

    Repo tidak memanggil commit(): transaksi diurus service. Pelanggaran aturan
    skema (unik, foreign key, CHECK, trigger) dibiarkan naik sebagai
    sqlite3.IntegrityError untuk diterjemahkan service.

    Args:
        conn: Koneksi database dari luar (dari buka_koneksi, atau ":memory:"
            di tes).
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, periode_panen: PeriodePanen) -> None:
        """Simpan periode baru.

        Jika ada periode aktif (tanggal selesai kosong) yang mulai lebih awal,
        trigger menutupnya sehari sebelum tanggal mulai periode baru.

        Args:
            periode_panen: Periode yang disimpan.

        Raises:
            sqlite3.IntegrityError: Tumpang tindih dengan periode lain, atau
                data melanggar CHECK di skema.
        """
        self.conn.execute(
            "INSERT INTO periode_panen (id_periode, nama_periode, tanggal_mulai, tanggal_selesai, deskripsi) VALUES (?, ?, ?, ?, ?)",
            (periode_panen.get_id_periode(), periode_panen.get_nama(), periode_panen.get_tanggal_mulai(), periode_panen.get_tanggal_selesai(), periode_panen.get_deskripsi()))

    def read(self, id_periode: str) -> PeriodePanen | None:
        """Ambil satu periode berdasarkan id.

        Args:
            id_periode: Id periode yang dicari.

        Returns:
            PeriodePanen, atau None jika tidak ada.
        """
        baris = self.conn.execute(
            "SELECT id_periode, nama_periode, tanggal_mulai, tanggal_selesai, deskripsi FROM periode_panen WHERE id_periode = ?",
            (id_periode,)).fetchone()
        if baris is None:
            return None
        
        return PeriodePanen(
            baris["nama_periode"],
            baris["tanggal_mulai"],
            baris["tanggal_selesai"],
            baris["deskripsi"],
            id_periode=baris["id_periode"]
        )

    def read_all(self) -> list[PeriodePanen]:
        """Ambil semua periode.

        Returns:
            Daftar PeriodePanen, urut berdasarkan tanggal mulai.
        """
        baris_list = self.conn.execute(
            "SELECT id_periode, nama_periode, tanggal_mulai, tanggal_selesai, deskripsi FROM periode_panen ORDER BY tanggal_mulai").fetchall()
        return [
            PeriodePanen(
                baris["nama_periode"],
                baris["tanggal_mulai"],
                baris["tanggal_selesai"],
                baris["deskripsi"],
                id_periode=baris["id_periode"]
            )
            for baris in baris_list
        ]

    def read_by_name(self, nama_periode: str) -> PeriodePanen | None:
        """Ambil satu periode berdasarkan nama.

        Args:
            nama_periode: Nama periode yang dicari.

        Returns:
            PeriodePanen, atau None jika tidak ada.
        """
        baris = self.conn.execute(
            "SELECT id_periode, nama_periode, tanggal_mulai, tanggal_selesai, deskripsi FROM periode_panen WHERE nama_periode = ?",
            (nama_periode,)).fetchone()
        if baris is None:
            return None
        
        return PeriodePanen(
            baris["nama_periode"],
            baris["tanggal_mulai"],
            baris["tanggal_selesai"],
            baris["deskripsi"],
            id_periode=baris["id_periode"]
        )

    def read_by_range(self, tanggal_mulai: str, tanggal_selesai: str) -> list[PeriodePanen]:
        """Ambil periode yang bersinggungan dengan rentang tanggal.

        Periode ikut terambil jika sebagian saja masuk rentang; tanggal batas
        ikut dihitung. Periode aktif (tanggal selesai kosong) dianggap belum
        berakhir, jadi ikut terambil untuk rentang apa pun setelah tanggal mulainya.

        Args:
            tanggal_mulai: Awal rentang, format YYYY-MM-DD.
            tanggal_selesai: Akhir rentang, format YYYY-MM-DD.

        Returns:
            Daftar PeriodePanen, urut berdasarkan tanggal mulai.
        """
        baris_list = self.conn.execute(
            "SELECT id_periode, nama_periode, tanggal_mulai, tanggal_selesai, deskripsi FROM periode_panen "
            "WHERE tanggal_mulai <= ? AND COALESCE(tanggal_selesai, '9999-12-31') >= ? "
            "ORDER BY tanggal_mulai",
            (tanggal_selesai, tanggal_mulai)).fetchall()

        return [
            PeriodePanen(
                baris["nama_periode"],
                baris["tanggal_mulai"],
                baris["tanggal_selesai"],
                baris["deskripsi"],
                id_periode=baris["id_periode"]
            )
            for baris in baris_list
        ]

    def read_by_date(self, tanggal: str) -> PeriodePanen | None:
        """Ambil periode yang bersinggungan dengan rentang tanggal.
                
        Mencari satu periode yang rentang tanggal mulai dan tanggal selesainya
        mencakup tanggal. Jika periode aktif, maka diambil periode aktif tersebut.

        Returns:
            PeriodePanen yang aktif, None jika tidak ada.
        """
        baris = self.conn.execute(
            "SELECT id_periode, nama_periode, tanggal_mulai, tanggal_selesai, deskripsi FROM periode_panen "
            "WHERE tanggal_mulai <= ? AND COALESCE(tanggal_selesai, '9999-12-31') >= ? "
            "ORDER BY tanggal_mulai DESC "
            "LIMIT 1",
            (tanggal, tanggal)).fetchone()
        if baris is None:
            return None
        
        return PeriodePanen(
            baris["nama_periode"],
            baris["tanggal_mulai"],
            baris["tanggal_selesai"],
            baris["deskripsi"],
            id_periode=baris["id_periode"]
        )

    def read_active_period(self) -> PeriodePanen | None:
        """Ambil periode aktif.
        
        Mengambil periode aktif terbaru.

        Returns:
            PeriodePanen yang aktif, None jika tidak ada.
        """
        baris = self.conn.execute(
            "SELECT id_periode, nama_periode, tanggal_mulai, tanggal_selesai, deskripsi "
            "FROM periode_panen "
            "WHERE tanggal_selesai IS NULL "
            "ORDER BY tanggal_mulai DESC "
            "LIMIT 1",
            ).fetchone()
        if baris is None:
            return None
        
        return PeriodePanen(
            baris["nama_periode"],
            baris["tanggal_mulai"],
            baris["tanggal_selesai"],
            baris["deskripsi"],
            id_periode=baris["id_periode"]
        )

    def is_periode_used(self, id_periode: str) -> bool:
        """Cek apakah periode sudah dipakai stok pohon.

        Catatan buah tidak dihitung, karena buah tidak terhubung langsung ke periode.

        Args:
            id_periode: Id periode yang dicek.

        Returns:
            True jika sudah dipakai, False jika belum.
        """
        baris = self.conn.execute(
            "SELECT COUNT(*) AS jumlah FROM stok_pohon WHERE id_periode = ?",
            (id_periode,)).fetchone()
        return baris["jumlah"] > 0

    def delete(self, id_periode: str) -> None:
        """Hapus periode. Tidak error jika id tidak ada.

        Catatan buah tidak ikut terhapus, karena buah tidak terhubung langsung ke periode.

        Args:
            id_periode: Id periode yang dihapus.

        Raises:
            sqlite3.IntegrityError: Periode masih dipakai stok pohon.
        """
        self.conn.execute(
            "DELETE FROM periode_panen WHERE id_periode = ?",
            (id_periode,))

    def update(self, periode_panen: PeriodePanen) -> None:
        """Simpan perubahan semua kolom periode. Tidak error jika id tidak ada.

        Args:
            periode_panen: Periode dengan data baru; dicocokkan lewat id_periode.

        Raises:
            sqlite3.IntegrityError: Hasilnya tumpang tindih dengan periode lain,
                atau data melanggar CHECK di skema.
        """
        self.conn.execute(
            "UPDATE periode_panen SET nama_periode = ?, tanggal_mulai = ?, tanggal_selesai = ?, deskripsi = ? WHERE id_periode = ?",
            (periode_panen.get_nama(), periode_panen.get_tanggal_mulai(), periode_panen.get_tanggal_selesai(), periode_panen.get_deskripsi(), periode_panen.get_id_periode()))
        