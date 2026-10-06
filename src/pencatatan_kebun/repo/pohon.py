import sqlite3
from typing import Optional

from pencatatan_kebun.models import Pohon


class RepoPohon:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def simpan(self, pohon: Pohon) -> None:
        self.conn.execute(
            "INSERT INTO pohon (id_pohon, nomor_pohon) VALUES (?, ?)",
            (pohon.get_id_pohon(), pohon.get_nomor_pohon()))

    def ambil(self, id_pohon: str) -> Optional[Pohon]:
        baris = self.conn.execute(
            "SELECT id_pohon, nomor_pohon FROM pohon WHERE id_pohon = ?",
            (id_pohon,)).fetchone()
        if baris is None:
            return None
        
        return Pohon(
            baris["nomor_pohon"],
            id_pohon=baris["id_pohon"]
        )

    def ambil_semua(self) -> list[Pohon]:
        baris_list = self.conn.execute(
            "SELECT id_pohon, nomor_pohon FROM pohon ORDER BY nomor_pohon").fetchall()
        
        return [
            Pohon(
                baris["nomor_pohon"],
                id_pohon=baris["id_pohon"]
            )
            for baris in baris_list
        ]

    def ambil_berdasarkan_nomor(self, nomor_pohon: int) -> Optional[Pohon]:
        baris = self.conn.execute(
            "SELECT id_pohon, nomor_pohon FROM pohon WHERE nomor_pohon = ?",
            (nomor_pohon,)).fetchone()
        if baris is None:
            return None
        
        return Pohon(
            baris["nomor_pohon"],
            id_pohon=baris["id_pohon"]
        )

    def ambil_berdasarkan_nomor_banyak(self, nomor_pohon: list[int]) -> list[Pohon]:
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

    def hapus(self, id_pohon: str) -> None:
        self.conn.execute(
            "DELETE FROM pohon WHERE id_pohon = ?",
            (id_pohon,))

    def perbarui(self, pohon: Pohon) -> None:
        self.conn.execute(
            "UPDATE pohon SET nomor_pohon = ? WHERE id_pohon = ?",
            (pohon.get_nomor_pohon(), pohon.get_id_pohon()))
        