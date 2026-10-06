import sqlite3
from typing import Optional

from pencatatan_kebun.models import PeriodePanen


class RepoPeriodePanen:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, periode_panen: PeriodePanen) -> None:
        self.conn.execute(
            "INSERT INTO periode_panen (id_periode, nama_periode, tanggal_mulai, tanggal_selesai, deskripsi) VALUES (?, ?, ?, ?, ?)",
            (periode_panen.get_id_periode(), periode_panen.get_nama(), periode_panen.get_tanggal_mulai(), periode_panen.get_tanggal_selesai(), periode_panen.get_deskripsi()))

    def read(self, id_periode: str) -> Optional[PeriodePanen]:
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

    def read_by_range(self, tanggal_mulai: str, tanggal_selesai: str) -> list[PeriodePanen]:
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

    def delete(self, id_periode: str) -> None:
        self.conn.execute(
            "DELETE FROM periode_panen WHERE id_periode = ?",
            (id_periode,))

    def update(self, periode_panen: PeriodePanen) -> None:
        self.conn.execute(
            "UPDATE periode_panen SET nama_periode = ?, tanggal_mulai = ?, tanggal_selesai = ?, deskripsi = ? WHERE id_periode = ?",
            (periode_panen.get_nama(), periode_panen.get_tanggal_mulai(), periode_panen.get_tanggal_selesai(), periode_panen.get_deskripsi(), periode_panen.get_id_periode()))
        