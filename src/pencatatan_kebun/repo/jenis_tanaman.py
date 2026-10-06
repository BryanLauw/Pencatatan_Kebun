import sqlite3
from typing import Optional

from pencatatan_kebun.models import JenisTanaman


class RepoJenisTanaman:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def simpan(self, jenis_tanaman: JenisTanaman) -> None:
        self.conn.execute(
            "INSERT INTO jenis_tanaman (id_jenis, nama_jenis, deskripsi) VALUES (?, ?, ?)",
            (jenis_tanaman.get_id_jenis(), jenis_tanaman.get_nama_jenis(), jenis_tanaman.get_deskripsi()))

    def ambil(self, id_jenis: str) -> Optional[JenisTanaman]:
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

    def ambil_semua(self) -> list[JenisTanaman]:
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

    def ambil_berdasarkan_nama(self, nama_jenis: str) -> Optional[JenisTanaman]:
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

    def ambil_berdasarkan_nama_banyak(self, nama_jenis: list[str]) -> list[JenisTanaman]:
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

    def hapus(self, id_jenis: str) -> None:
        self.conn.execute(
            "DELETE FROM jenis_tanaman WHERE id_jenis = ?",
            (id_jenis,))

    def perbarui(self, jenis_tanaman: JenisTanaman) -> None:
        self.conn.execute(
            "UPDATE jenis_tanaman SET nama_jenis = ?, deskripsi = ? WHERE id_jenis = ?",
            (jenis_tanaman.get_nama_jenis(), jenis_tanaman.get_deskripsi(), jenis_tanaman.get_id_jenis()))
        