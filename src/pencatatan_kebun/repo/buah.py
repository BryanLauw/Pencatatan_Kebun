import sqlite3
from typing import Optional

from pencatatan_kebun.models import Buah
from pencatatan_kebun.repo.pohon import RepoPohon
from pencatatan_kebun.repo.varietas import RepoVarietas
from pencatatan_kebun.repo.keterangan_buah import RepoKeteranganBuah


class RepoBuah:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def simpan(self, buah: Buah) -> None:
        self.conn.execute(
            "INSERT INTO buah (id_buah, id_pohon, id_varietas, tanggal_panen, id_keterangan, bobot) VALUES (?, ?, ?, ?, ?, ?)",
            (buah.get_id_buah(), buah.get_pohon().get_id_pohon(), buah.get_varietas().get_id_varietas(), buah.get_tanggal_panen(), buah.get_keterangan().get_id_keterangan(), buah.get_bobot()))

    def ambil(self, id_buah: str) -> Optional[Buah]:
        baris = self.conn.execute(
            "SELECT id_buah, id_pohon, id_varietas, tanggal_panen, id_keterangan, bobot FROM buah WHERE id_buah = ?",
            (id_buah,)).fetchone()
        if baris is None:
            return None
        
        pohon = RepoPohon(self.conn).ambil(baris["id_pohon"])
        varietas = RepoVarietas(self.conn).ambil(baris["id_varietas"])
        keterangan_buah = RepoKeteranganBuah(self.conn).ambil(baris["id_keterangan"])

        return Buah(
            pohon,
            varietas,
            baris["bobot"],
            keterangan_buah,
            baris["tanggal_panen"],
            id_buah=baris["id_buah"]
        )

    def ambil_semua(self) -> list[Buah]:
        baris_list = self.conn.execute(
            "SELECT b.id_buah, b.id_pohon, b.id_varietas, b.tanggal_panen, b.id_keterangan, b.bobot FROM buah b "
            "JOIN pohon p ON p.id_pohon = b.id_pohon "
            "ORDER BY b.tanggal_panen, p.nomor_pohon").fetchall()
        
        return [
            Buah(
                RepoPohon(self.conn).ambil(baris["id_pohon"]),
                RepoVarietas(self.conn).ambil(baris["id_varietas"]),
                baris["bobot"],
                RepoKeteranganBuah(self.conn).ambil(baris["id_keterangan"]),
                baris["tanggal_panen"],
                id_buah=baris["id_buah"]
            )
            for baris in baris_list
        ]

    def ambil_berdasarkan_tanggal_panen(self, tanggal_panen: str) -> list[Buah]:
        baris_list = self.conn.execute(
            "SELECT b.id_buah, b.id_pohon, b.id_varietas, b.tanggal_panen, b.id_keterangan, b.bobot FROM buah b "
            "JOIN pohon p ON p.id_pohon = b.id_pohon "
            "WHERE b.tanggal_panen = ? ORDER BY p.nomor_pohon",
            (tanggal_panen,)).fetchall()
        
        return [
            Buah(
                RepoPohon(self.conn).ambil(baris["id_pohon"]),
                RepoVarietas(self.conn).ambil(baris["id_varietas"]),
                baris["bobot"],
                RepoKeteranganBuah(self.conn).ambil(baris["id_keterangan"]),
                baris["tanggal_panen"],
                id_buah=baris["id_buah"]
            )
            for baris in baris_list
        ]

    def ambil_berdasarkan_tanggal_panen_banyak(self, tanggal_panen: list[str]) -> list[Buah]:
        baris_list = self.conn.execute(
            "SELECT b.id_buah, b.id_pohon, b.id_varietas, b.tanggal_panen, b.id_keterangan, b.bobot FROM buah b "
            "JOIN pohon p ON p.id_pohon = b.id_pohon "
            "WHERE b.tanggal_panen IN ({}) ORDER BY b.tanggal_panen, p.nomor_pohon".format(",".join("?" * len(tanggal_panen))),
            tuple(tanggal_panen)).fetchall()

        return [
            Buah(
                RepoPohon(self.conn).ambil(baris["id_pohon"]),
                RepoVarietas(self.conn).ambil(baris["id_varietas"]),
                baris["bobot"],
                RepoKeteranganBuah(self.conn).ambil(baris["id_keterangan"]),
                baris["tanggal_panen"],
                id_buah=baris["id_buah"]
            )
            for baris in baris_list
        ]

    def hapus(self, id_buah: str) -> None:
        self.conn.execute(
            "DELETE FROM buah WHERE id_buah = ?",
            (id_buah,))

    def perbarui(self, buah: Buah) -> None:
        self.conn.execute(
            "UPDATE buah SET id_pohon = ?, id_varietas = ?, tanggal_panen = ?, id_keterangan = ?, bobot = ? WHERE id_buah = ?",
            (buah.get_pohon().get_id_pohon(), buah.get_varietas().get_id_varietas(), buah.get_tanggal_panen(), buah.get_keterangan().get_id_keterangan(), buah.get_bobot(), buah.get_id_buah()))
