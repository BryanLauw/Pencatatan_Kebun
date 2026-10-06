import sqlite3
from typing import Optional

from pencatatan_kebun.models import KeteranganBuah


class RepoKeteranganBuah:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def simpan(self, keterangan_buah: KeteranganBuah) -> None:
        self.conn.execute(
            "INSERT INTO keterangan_buah (id_keterangan, nama_keterangan, deskripsi) VALUES (?, ?, ?)",
            (keterangan_buah.get_id_keterangan(), keterangan_buah.get_nama_keterangan(), keterangan_buah.get_deskripsi()))

    def ambil(self, id_keterangan: str) -> Optional[KeteranganBuah]:
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

    def ambil_semua(self) -> list[KeteranganBuah]:
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

    def ambil_berdasarkan_nama(self, nama_keterangan: str) -> Optional[KeteranganBuah]:
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

    def ambil_berdasarkan_nama_banyak(self, nama_keterangan: list[str]) -> list[KeteranganBuah]:
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

    def hapus(self, id_keterangan: str) -> None:
        self.conn.execute(
            "DELETE FROM keterangan_buah WHERE id_keterangan = ?",
            (id_keterangan,))

    def perbarui(self, keterangan_buah: KeteranganBuah) -> None:
        self.conn.execute(
            "UPDATE keterangan_buah SET nama_keterangan = ?, deskripsi = ? WHERE id_keterangan = ?",
            (keterangan_buah.get_nama_keterangan(), keterangan_buah.get_deskripsi(), keterangan_buah.get_id_keterangan()))
