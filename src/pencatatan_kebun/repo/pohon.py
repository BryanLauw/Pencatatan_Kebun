import sqlite3
from typing import Optional

from pencatatan_kebun.models import Pohon


class RepoPohon:
    """Akses tabel pohon. Pohon hanya punya nomor dan tidak terhubung ke jenis.

    Koneksi dikirim dari luar (dari buka_koneksi, atau ":memory:" di tes).
    Repo tidak memanggil commit(): transaksi diurus service. Pelanggaran aturan
    skema (unik, foreign key, CHECK, trigger) dibiarkan naik sebagai
    sqlite3.IntegrityError untuk diterjemahkan service.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, pohon: Pohon) -> None:
        self.conn.execute(
            "INSERT INTO pohon (id_pohon, nomor_pohon) VALUES (?, ?)",
            (pohon.get_id_pohon(), pohon.get_nomor_pohon()))

    def read(self, id_pohon: str) -> Optional[Pohon]:
        """Pohon dengan id tersebut, atau None jika tidak ada."""
        baris = self.conn.execute(
            "SELECT id_pohon, nomor_pohon FROM pohon WHERE id_pohon = ?",
            (id_pohon,)).fetchone()
        if baris is None:
            return None
        
        return Pohon(
            baris["nomor_pohon"],
            id_pohon=baris["id_pohon"]
        )

    def read_all(self) -> list[Pohon]:
        """Semua pohon, urut berdasarkan nomor."""
        baris_list = self.conn.execute(
            "SELECT id_pohon, nomor_pohon FROM pohon ORDER BY nomor_pohon").fetchall()
        
        return [
            Pohon(
                baris["nomor_pohon"],
                id_pohon=baris["id_pohon"]
            )
            for baris in baris_list
        ]

    def read_by_number(self, nomor_pohon: int) -> Optional[Pohon]:
        """Pohon dengan nomor tersebut, atau None jika tidak ada."""
        baris = self.conn.execute(
            "SELECT id_pohon, nomor_pohon FROM pohon WHERE nomor_pohon = ?",
            (nomor_pohon,)).fetchone()
        if baris is None:
            return None
        
        return Pohon(
            baris["nomor_pohon"],
            id_pohon=baris["id_pohon"]
        )

    def read_by_numbers(self, nomor_pohon: list[int]) -> list[Pohon]:
        """Pohon yang nomornya ada di daftar, urut berdasarkan nomor.

        Nomor yang tidak ditemukan dilewati; daftar kosong menghasilkan [].
        """
        baris_list = self.conn.execute(
            "SELECT id_pohon, nomor_pohon FROM pohon WHERE nomor_pohon IN ({}) ORDER BY nomor_pohon".format(",".join("?" * len(nomor_pohon))),
            tuple(nomor_pohon)).fetchall()

        return [
            Pohon(
                baris["nomor_pohon"],
                id_pohon=baris["id_pohon"]
            )
            for baris in baris_list
        ]

    def delete(self, id_pohon: str) -> None:
        """Hapus pohon. Tidak error jika id tidak ada.

        Ditolak (IntegrityError) jika pohon sudah punya catatan buah.
        """
        self.conn.execute(
            "DELETE FROM pohon WHERE id_pohon = ?",
            (id_pohon,))

    def update(self, pohon: Pohon) -> None:
        """Simpan perubahan nomor pohon. Tidak error jika id tidak ada.

        Ditolak (IntegrityError) jika nomor sudah dipakai pohon lain.
        """
        self.conn.execute(
            "UPDATE pohon SET nomor_pohon = ? WHERE id_pohon = ?",
            (pohon.get_nomor_pohon(), pohon.get_id_pohon()))
        