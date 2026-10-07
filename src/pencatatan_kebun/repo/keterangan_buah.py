import sqlite3
from typing import Optional

from pencatatan_kebun.models import KeteranganBuah


class RepoKeteranganBuah:
    """Akses tabel keterangan_buah (kondisi buah, mis. "Baik" atau "Busuk").

    Koneksi dikirim dari luar (dari buka_koneksi, atau ":memory:" di tes).
    Repo tidak memanggil commit(): transaksi diurus service. Pelanggaran aturan
    skema (unik, foreign key, CHECK, trigger) dibiarkan naik sebagai
    sqlite3.IntegrityError untuk diterjemahkan service.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, keterangan_buah: KeteranganBuah) -> None:
        self.conn.execute(
            "INSERT INTO keterangan_buah (id_keterangan, nama_keterangan, deskripsi) VALUES (?, ?, ?)",
            (keterangan_buah.get_id_keterangan(), keterangan_buah.get_nama_keterangan(), keterangan_buah.get_deskripsi()))

    def read(self, id_keterangan: str) -> Optional[KeteranganBuah]:
        """Keterangan dengan id tersebut, atau None jika tidak ada."""
        baris = self.conn.execute(
            "SELECT id_keterangan, nama_keterangan, deskripsi FROM keterangan_buah WHERE id_keterangan = ?",
            (id_keterangan,)).fetchone()
        if baris is None:
            return None
        
        return KeteranganBuah(
            baris["nama_keterangan"],
            baris["deskripsi"],
            id_keterangan=baris["id_keterangan"]
        )

    def read_all(self) -> list[KeteranganBuah]:
        """Semua keterangan, urut berdasarkan nama (tanpa membedakan huruf besar/kecil)."""
        baris_list = self.conn.execute(
            "SELECT id_keterangan, nama_keterangan, deskripsi FROM keterangan_buah ORDER BY nama_keterangan").fetchall()
        
        return [
            KeteranganBuah(
                baris["nama_keterangan"],
                baris["deskripsi"],
                id_keterangan=baris["id_keterangan"]
            )
            for baris in baris_list
        ]

    def read_by_name(self, nama_keterangan: str) -> Optional[KeteranganBuah]:
        """Keterangan dengan nama tersebut, atau None. Tidak membedakan huruf besar/kecil."""
        baris = self.conn.execute(
            "SELECT id_keterangan, nama_keterangan, deskripsi FROM keterangan_buah WHERE nama_keterangan = ?",
            (nama_keterangan,)).fetchone()
        if baris is None:
            return None
        
        return KeteranganBuah(
            baris["nama_keterangan"],
            baris["deskripsi"],
            id_keterangan=baris["id_keterangan"]
        )

    def read_by_names(self, nama_keterangan: list[str]) -> list[KeteranganBuah]:
        """Keterangan yang namanya ada di daftar, urut berdasarkan nama.

        Tidak membedakan huruf besar/kecil. Nama yang tidak ditemukan dilewati;
        daftar kosong menghasilkan [].
        """
        baris_list = self.conn.execute(
            "SELECT id_keterangan, nama_keterangan, deskripsi FROM keterangan_buah WHERE nama_keterangan IN ({}) ORDER BY nama_keterangan".format(",".join("?" * len(nama_keterangan))),
            tuple(nama_keterangan)).fetchall()

        return [
            KeteranganBuah(
                baris["nama_keterangan"],
                baris["deskripsi"],
                id_keterangan=baris["id_keterangan"]
            )
            for baris in baris_list
        ]

    def delete(self, id_keterangan: str) -> None:
        """Hapus keterangan. Tidak error jika id tidak ada.

        Ditolak (IntegrityError) jika masih dipakai catatan buah.
        """
        self.conn.execute(
            "DELETE FROM keterangan_buah WHERE id_keterangan = ?",
            (id_keterangan,))

    def update(self, keterangan_buah: KeteranganBuah) -> None:
        """Simpan perubahan nama dan deskripsi. Tidak error jika id tidak ada."""
        self.conn.execute(
            "UPDATE keterangan_buah SET nama_keterangan = ?, deskripsi = ? WHERE id_keterangan = ?",
            (keterangan_buah.get_nama_keterangan(), keterangan_buah.get_deskripsi(), keterangan_buah.get_id_keterangan()))
