import sqlite3
from typing import Optional

from pencatatan_kebun.models import JenisTanaman, Varietas
from pencatatan_kebun.repo.jenis_tanaman import RepoJenisTanaman


class RepoVarietas:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def simpan(self, varietas: Varietas) -> None:
        self.conn.execute(
            "INSERT INTO varietas (id_varietas, nama_varietas, id_jenis, deskripsi) VALUES (?, ?, ?, ?)",
            (varietas.get_id_varietas(), varietas.get_nama_varietas(), varietas.get_jenis().get_id_jenis(), varietas.get_deskripsi()))

    def ambil(self, id_varietas: str) -> Optional[Varietas]:
        baris = self.conn.execute(
            "SELECT id_varietas, nama_varietas, id_jenis, deskripsi FROM varietas WHERE id_varietas = ?",
            (id_varietas,)).fetchone()
        if baris is None:
            return None
        
        jenis_tanaman = RepoJenisTanaman(self.conn).ambil(baris["id_jenis"])
        return Varietas(
            baris["nama_varietas"],
            jenis_tanaman,
            baris["deskripsi"],
            id_varietas=baris["id_varietas"]
        )

    def ambil_semua(self) -> list[Varietas]:
        baris_list = self.conn.execute(
            "SELECT v.id_varietas, v.nama_varietas, v.id_jenis, v.deskripsi FROM varietas v "
            "JOIN jenis_tanaman j ON j.id_jenis = v.id_jenis "
            "ORDER BY j.nama_jenis, v.nama_varietas").fetchall()
        
        return [
            Varietas(
                baris["nama_varietas"],
                RepoJenisTanaman(self.conn).ambil(baris["id_jenis"]),
                baris["deskripsi"],
                id_varietas=baris["id_varietas"]
            )
            for baris in baris_list
        ]

    def ambil_berdasarkan_nama(self, nama_varietas: str, jenis: JenisTanaman) -> Optional[Varietas]:
        baris = self.conn.execute(
            "SELECT id_varietas, nama_varietas, id_jenis, deskripsi FROM varietas WHERE nama_varietas = ? AND id_jenis = ?",
            (nama_varietas, jenis.get_id_jenis())).fetchone()
        if baris is None:
            return None
        
        jenis_tanaman = RepoJenisTanaman(self.conn).ambil(baris["id_jenis"])
        return Varietas(
            baris["nama_varietas"],
            jenis_tanaman,
            baris["deskripsi"],
            id_varietas=baris["id_varietas"]
        )

    def ambil_berdasarkan_nama_banyak(self, nama_varietas: list[str]) -> list[Varietas]:
        baris_list = self.conn.execute(
            "SELECT v.id_varietas, v.nama_varietas, v.id_jenis, v.deskripsi FROM varietas v "
            "JOIN jenis_tanaman j ON j.id_jenis = v.id_jenis "
            "WHERE v.nama_varietas IN ({}) ORDER BY j.nama_jenis, v.nama_varietas".format(",".join("?" * len(nama_varietas))),
            tuple(nama_varietas)).fetchall()

        return [
            Varietas(
                baris["nama_varietas"],
                RepoJenisTanaman(self.conn).ambil(baris["id_jenis"]),
                baris["deskripsi"],
                id_varietas=baris["id_varietas"]
            )
            for baris in baris_list
        ]

    def hapus(self, id_varietas: str) -> None:
        self.conn.execute(
            "DELETE FROM varietas WHERE id_varietas = ?",
            (id_varietas,))

    def perbarui(self, varietas: Varietas) -> None:
        self.conn.execute(
            "UPDATE varietas SET nama_varietas = ?, id_jenis = ?, deskripsi = ? WHERE id_varietas = ?",
            (varietas.get_nama_varietas(), varietas.get_jenis().get_id_jenis(), varietas.get_deskripsi(), varietas.get_id_varietas()))
        