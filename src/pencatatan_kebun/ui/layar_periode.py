"""Layar Periode Panen: daftar periode, buka, ubah, tutup, dan hapus."""
import tkinter as tk
from collections.abc import Callable
from datetime import date
from tkinter import messagebox, ttk

from pencatatan_kebun.models import PeriodePanen
from pencatatan_kebun.services.periode import PeriodeService
from pencatatan_kebun.ui.format import kalimat, tanggal_ke_tampil
from pencatatan_kebun.ui.kalender import EntryTanggal, sehari_setelah
from pencatatan_kebun.ui.komponen import (
    PanelCrud,
    baris_isian,
    jalankan_aman,
    set_entry,
    skala,
)


class LayarPeriode(PanelCrud):
    """Tab Periode Panen.

    Periode aktif (tanggal selesai kosong) diberi warna hijau. Membuka periode
    baru otomatis menutup periode aktif sehari sebelum tanggal mulai periode
    baru (diatur trigger di skema).

    Args:
        parent: Widget induk (Notebook jendela utama).
        service: PeriodeService.
        saat_berubah: Dipanggil setelah periode berubah, agar layar lain
            (stok, dashboard) memuat ulang daftar periode.
    """

    nama_data = "periode"
    kolom = [("Nama periode", 200), ("Mulai", 120), ("Selesai", 120), ("Status", 100),
             ("Deskripsi", 250)]

    def __init__(self, parent: tk.Widget, service: PeriodeService,
                 saat_berubah: Callable[[], None]):
        self._aktif_sebelum_tambah: PeriodePanen | None = None
        self._saat_periode_berubah = saat_berubah
        super().__init__(parent, service, self._berubah)
        self.tabel.tree.tag_configure("aktif", background="#dff3dc")

    def _berubah(self):
        self.muat_ulang()
        self._saat_periode_berubah()

    def buat_form(self, frame):
        self.entry_nama = baris_isian(frame, 0, "Nama periode", ttk.Entry(frame, width=30))
        # Tanggal selesai harus setelah tanggal mulai: tanggal sebelumnya diblok.
        self.tgl_mulai = baris_isian(frame, 1, "Tanggal mulai", EntryTanggal(
            frame, "tanggal_mulai", "Tanggal mulai", hari_ini=False,
            saat_berubah=lambda t: self.tgl_selesai.set_batas(batas_awal=sehari_setelah(t))))
        self.tgl_selesai = baris_isian(frame, 2, "Tanggal selesai", EntryTanggal(
            frame, "tanggal_selesai", "Tanggal selesai", hari_ini=False, boleh_kosong=True))
        self.entry_deskripsi = baris_isian(frame, 3, "Deskripsi", ttk.Entry(frame, width=30))
        ttk.Label(frame, text="Kosongkan tanggal selesai jika periode masih berjalan.",
                  foreground="#555").grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.info = ttk.Label(frame, foreground="#9a6700", wraplength=skala(frame, 380))
        self.info.grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.isian = {"nama_periode": self.entry_nama, "tanggal_mulai": self.tgl_mulai.entry,
                      "tanggal_selesai": self.tgl_selesai.entry}

    def buat_tombol(self, frame):
        self.tombol_tutup = ttk.Button(frame, text="Tutup periode", command=self._tutup)
        self.tombol_tutup.pack(anchor="w", pady=(6, 0))

    def data(self):
        # Periode terbaru di atas.
        return list(reversed(self.service.daftar_periode()))

    def id_objek(self, objek):
        return objek.get_id_periode()

    def nilai_baris(self, objek):
        selesai = objek.get_tanggal_selesai()
        return (objek.get_nama(), tanggal_ke_tampil(objek.get_tanggal_mulai()),
                tanggal_ke_tampil(selesai) if selesai else "-",
                self._status(objek), objek.get_deskripsi() or "")

    @staticmethod
    def _status(objek):
        """Aktif: tanggal selesai kosong. Berjalan: selesai hari ini atau nanti."""
        if objek.get_tanggal_selesai() is None:
            return "Aktif"
        return "Berjalan" if objek.is_active() else "Selesai"

    def tag_baris(self, objek):
        return ("aktif",) if objek.get_tanggal_selesai() is None else ()

    def isi_form(self, objek):
        set_entry(self.entry_nama, objek.get_nama())
        self.tgl_mulai.set_db(objek.get_tanggal_mulai())
        self.tgl_selesai.set_db(objek.get_tanggal_selesai())
        set_entry(self.entry_deskripsi, objek.get_deskripsi())

    def kosongkan_form(self):
        set_entry(self.entry_nama, "")
        self.tgl_mulai.isi_hari_ini()
        self.tgl_selesai.kosongkan()
        set_entry(self.entry_deskripsi, "")
        self.entry_nama.focus_set()

    def saat_mode(self, objek):
        aktif = objek is not None and objek.get_tanggal_selesai() is None
        self.tombol_tutup.state(["!disabled"] if aktif else ["disabled"])
        teks = ""
        if objek is None:
            lama = self.service.periode_aktif()
            if lama is not None:
                teks = (f"Periode aktif \"{lama.get_nama()}\" akan otomatis ditutup sehari "
                        "sebelum tanggal mulai periode baru.")
        self.info.configure(text=teks)

    def simpan(self, id_lama):
        nama = self.entry_nama.get()
        mulai, selesai = self.tgl_mulai.get_db(), self.tgl_selesai.get_db()
        deskripsi = self.entry_deskripsi.get().strip()
        if id_lama is None:
            self._aktif_sebelum_tambah = self.service.periode_aktif()
            return self.service.buka_periode(nama, mulai, selesai, deskripsi)
        return self.service.ubah_periode(id_lama, nama, mulai, selesai, deskripsi)

    def setelah_tambah(self, objek):
        super().setelah_tambah(objek)
        lama = self._aktif_sebelum_tambah
        if lama is None:
            return
        for periode in self.service.daftar_periode():
            if periode.get_id_periode() == lama.get_id_periode() and periode.get_tanggal_selesai():
                self.tampilkan_status(
                    f"{kalimat(self.nama(objek))} tersimpan. Periode {lama.get_nama()} "
                    f"otomatis ditutup per {tanggal_ke_tampil(periode.get_tanggal_selesai())}.")

    def hapus(self, objek):
        self.service.hapus_periode(objek.get_id_periode())

    def nama(self, objek):
        return f"periode {objek.get_nama()}"

    def _tutup(self):
        objek = self.dipilih
        if objek is None:
            return
        # Tanggal selesai di form dipakai jika diisi; jika kosong, hari ini.
        berhasil, tanggal = jalankan_aman(self, self.tgl_selesai.get_db, self.isian)
        if not berhasil:
            return
        tampil = tanggal_ke_tampil(tanggal or date.today().isoformat())
        if not messagebox.askyesno("Tutup periode",
                                   f"Tutup periode {objek.get_nama()} per tanggal {tampil}?",
                                   parent=self):
            return
        berhasil, hasil = jalankan_aman(
            self, lambda: self.service.tutup_periode(objek.get_id_periode(), tanggal), self.isian)
        if berhasil:
            self.tampilkan_status(f"{kalimat(self.nama(hasil))} ditutup.")
            self.dipilih = hasil
            self.saat_berubah()
