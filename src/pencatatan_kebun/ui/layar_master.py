"""Layar Data Master: jenis tanaman, varietas, pohon, dan keterangan buah."""
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from pencatatan_kebun.models import JenisTanaman, KeteranganBuah, Varietas
from pencatatan_kebun.services.master import MasterService
from pencatatan_kebun.ui.format import teks_ke_int
from pencatatan_kebun.ui.komponen import (
    ComboObjek,
    PanelCrud,
    baris_isian,
    set_entry,
    wajib_pilih,
)


def label_jenis(jenis: JenisTanaman) -> str:
    return jenis.get_nama_jenis()


def label_varietas(varietas: Varietas) -> str:
    """Nama varietas beserta jenisnya, mis. "Durian - Musang King"."""
    return f"{varietas.get_jenis().get_nama_jenis()} - {varietas.get_nama_varietas()}"


def id_jenis(jenis: JenisTanaman) -> str:
    return jenis.get_id_jenis()


def id_varietas(varietas: Varietas) -> str:
    return varietas.get_id_varietas()


# ---- jenis tanaman ----

class SubTabJenis(PanelCrud):
    nama_data = "jenis"
    kolom = [("Jenis", 200), ("Deskripsi", 350)]

    def buat_form(self, frame):
        self.entry_nama = baris_isian(frame, 0, "Nama jenis", ttk.Entry(frame, width=30))
        self.entry_deskripsi = baris_isian(frame, 1, "Deskripsi", ttk.Entry(frame, width=30))
        self.isian = {"nama_jenis": self.entry_nama}

    def data(self):
        return self.service.daftar_jenis()

    def id_objek(self, objek):
        return objek.get_id_jenis()

    def nilai_baris(self, objek):
        return (objek.get_nama_jenis(), objek.get_deskripsi() or "")

    def isi_form(self, objek):
        set_entry(self.entry_nama, objek.get_nama_jenis())
        set_entry(self.entry_deskripsi, objek.get_deskripsi())

    def kosongkan_form(self):
        set_entry(self.entry_nama, "")
        set_entry(self.entry_deskripsi, "")
        self.entry_nama.focus_set()

    def simpan(self, id_lama):
        nama, deskripsi = self.entry_nama.get(), self.entry_deskripsi.get().strip()
        if id_lama is None:
            return self.service.tambah_jenis(nama, deskripsi)
        return self.service.ubah_jenis(id_lama, nama, deskripsi)

    def hapus(self, objek):
        self.service.hapus_jenis(objek.get_id_jenis())

    def nama(self, objek):
        return f"jenis {objek.get_nama_jenis()}"


# ---- varietas ----

class SubTabVarietas(PanelCrud):
    nama_data = "varietas"
    kolom = [("Jenis", 150), ("Varietas", 200), ("Deskripsi", 300)]

    def buat_filter(self, frame):
        ttk.Label(frame, text="Tampilkan jenis").pack(side="left", padx=(0, 8))
        self.filter_jenis = ComboObjek(frame, label_jenis, id_jenis, label_kosong="(Semua jenis)")
        self.filter_jenis.pack(side="left")
        self.filter_jenis.bind("<<ComboboxSelected>>", lambda _e: self.muat_tabel())

    def buat_form(self, frame):
        self.combo_jenis = baris_isian(frame, 0, "Jenis", ComboObjek(frame, label_jenis, id_jenis))
        self.entry_nama = baris_isian(frame, 1, "Nama varietas", ttk.Entry(frame, width=30))
        self.entry_deskripsi = baris_isian(frame, 2, "Deskripsi", ttk.Entry(frame, width=30))
        self.isian = {"id_jenis": self.combo_jenis, "nama_varietas": self.entry_nama}

    def muat_dropdown(self):
        daftar = self.service.daftar_jenis()
        self.filter_jenis.isi(daftar)
        self.combo_jenis.isi(daftar)

    def data(self):
        return self.service.daftar_varietas(self.filter_jenis.terpilih())

    def id_objek(self, objek):
        return objek.get_id_varietas()

    def nilai_baris(self, objek):
        return (objek.get_jenis().get_nama_jenis(), objek.get_nama_varietas(),
                objek.get_deskripsi() or "")

    def isi_form(self, objek):
        self.combo_jenis.pilih_id(objek.get_jenis().get_id_jenis())
        set_entry(self.entry_nama, objek.get_nama_varietas())
        set_entry(self.entry_deskripsi, objek.get_deskripsi())

    def kosongkan_form(self):
        # Jenis mengikuti filter, supaya menambah beberapa varietas satu jenis cepat.
        if not self.combo_jenis.pilih_id(self.filter_jenis.id_terpilih()):
            self.combo_jenis.kosongkan()
        set_entry(self.entry_nama, "")
        set_entry(self.entry_deskripsi, "")
        self.entry_nama.focus_set()

    def simpan(self, id_lama):
        jenis = wajib_pilih(self.combo_jenis.terpilih(), "Jenis", "id_jenis")
        nama, deskripsi = self.entry_nama.get(), self.entry_deskripsi.get().strip()
        if id_lama is None:
            return self.service.tambah_varietas(jenis, nama, deskripsi)
        return self.service.ubah_varietas(id_lama, jenis, nama, deskripsi)

    def hapus(self, objek):
        self.service.hapus_varietas(objek.get_id_varietas())

    def nama(self, objek):
        return f"varietas {label_varietas(objek)}"


# ---- pohon ----

class SubTabPohon(PanelCrud):
    nama_data = "pohon"
    kolom = [("Jenis", 150), ("Varietas", 200), ("Nomor pohon", 120)]

    def buat_filter(self, frame):
        ttk.Label(frame, text="Tampilkan jenis").pack(side="left", padx=(0, 8))
        self.filter_jenis = ComboObjek(frame, label_jenis, id_jenis, label_kosong="(Semua jenis)",
                                       width=18)
        self.filter_jenis.pack(side="left")
        ttk.Label(frame, text="varietas").pack(side="left", padx=8)
        self.filter_varietas = ComboObjek(frame, lambda v: v.get_nama_varietas(), id_varietas,
                                          label_kosong="(Semua varietas)", width=20)
        self.filter_varietas.pack(side="left")
        self.filter_jenis.bind("<<ComboboxSelected>>", lambda _e: self._ganti_filter_jenis())
        self.filter_varietas.bind("<<ComboboxSelected>>", lambda _e: self.muat_tabel())

    def _ganti_filter_jenis(self):
        self._isi_filter_varietas()
        self.muat_tabel()

    def _isi_filter_varietas(self):
        jenis = self.filter_jenis.terpilih()
        self.filter_varietas.isi(self.service.daftar_varietas(jenis) if jenis is not None else [])

    def buat_form(self, frame):
        self.combo_varietas = baris_isian(frame, 0, "Varietas",
                                           ComboObjek(frame, label_varietas, id_varietas, width=30))
        self.entry_nomor = baris_isian(frame, 1, "Nomor pohon", ttk.Entry(frame, width=10))
        self.isian = {"id_varietas": self.combo_varietas, "nomor_pohon": self.entry_nomor}

    def muat_dropdown(self):
        self.filter_jenis.isi(self.service.daftar_jenis())
        self._isi_filter_varietas()
        self.combo_varietas.isi(self.service.daftar_varietas())

    def data(self):
        varietas = self.filter_varietas.terpilih()
        if varietas is not None:
            return self.service.daftar_pohon(varietas)
        daftar = self.service.daftar_pohon()
        jenis = self.filter_jenis.terpilih()
        if jenis is not None:
            daftar = [p for p in daftar
                      if p.get_varietas().get_jenis().get_id_jenis() == jenis.get_id_jenis()]
        return daftar

    def id_objek(self, objek):
        return objek.get_id_pohon()

    def nilai_baris(self, objek):
        varietas = objek.get_varietas()
        return (varietas.get_jenis().get_nama_jenis(), varietas.get_nama_varietas(),
                objek.get_nomor_pohon())

    def isi_form(self, objek):
        self.combo_varietas.pilih_id(objek.get_varietas().get_id_varietas())
        set_entry(self.entry_nomor, objek.get_nomor_pohon())

    def kosongkan_form(self):
        if not self.combo_varietas.pilih_id(self.filter_varietas.id_terpilih()):
            self.combo_varietas.kosongkan()
        set_entry(self.entry_nomor, "")
        self.entry_nomor.focus_set()

    def simpan(self, id_lama):
        varietas = wajib_pilih(self.combo_varietas.terpilih(), "Varietas", "id_varietas")
        nomor = teks_ke_int(self.entry_nomor.get())
        if id_lama is None:
            return self.service.tambah_pohon(varietas, nomor)
        return self.service.ubah_pohon(id_lama, varietas, nomor)

    def setelah_tambah(self, objek):
        # Tetap di mode tambah dengan nomor berikutnya, supaya mendaftarkan
        # banyak pohon cukup menekan Enter berulang kali.
        self.baru()
        self.combo_varietas.pilih_id(objek.get_varietas().get_id_varietas())
        set_entry(self.entry_nomor, objek.get_nomor_pohon() + 1)
        self.entry_nomor.select_range(0, "end")

    def hapus(self, objek):
        self.service.hapus_pohon(objek.get_id_pohon())

    def nama(self, objek):
        return f"pohon {label_varietas(objek.get_varietas())} nomor {objek.get_nomor_pohon()}"


# ---- keterangan buah ----

class SubTabKeterangan(PanelCrud):
    nama_data = "keterangan"
    kolom = [("Keterangan", 200), ("Deskripsi", 350)]

    def buat_form(self, frame):
        self.entry_nama = baris_isian(frame, 0, "Nama keterangan", ttk.Entry(frame, width=30))
        self.entry_deskripsi = baris_isian(frame, 1, "Deskripsi", ttk.Entry(frame, width=30))
        self.isian = {"nama_keterangan": self.entry_nama}

    def data(self):
        return self.service.daftar_keterangan()

    def id_objek(self, objek):
        return objek.get_id_keterangan()

    def nilai_baris(self, objek):
        return (objek.get_nama_keterangan(), objek.get_deskripsi() or "")

    def isi_form(self, objek):
        set_entry(self.entry_nama, objek.get_nama_keterangan())
        set_entry(self.entry_deskripsi, objek.get_deskripsi())

    def kosongkan_form(self):
        set_entry(self.entry_nama, "")
        set_entry(self.entry_deskripsi, "")
        self.entry_nama.focus_set()

    def simpan(self, id_lama):
        nama, deskripsi = self.entry_nama.get(), self.entry_deskripsi.get().strip()
        if id_lama is None:
            return self.service.tambah_keterangan(nama, deskripsi)
        return self.service.ubah_keterangan(id_lama, nama, deskripsi)

    def hapus(self, objek: KeteranganBuah):
        self.service.hapus_keterangan(objek.get_id_keterangan())

    def nama(self, objek: KeteranganBuah):
        return f"keterangan {objek.get_nama_keterangan()}"


class LayarMaster(ttk.Frame):
    """Tab Data Master berisi sub-tab Jenis, Varietas, Pohon, dan Keterangan.

    Args:
        parent: Widget induk (Notebook jendela utama).
        service: MasterService.
        saat_master_berubah: Dipanggil setelah data master berubah, agar
            dropdown di layar lain ikut dimuat ulang. Boleh None.
    """

    def __init__(self, parent: tk.Widget, service: MasterService,
                 saat_master_berubah: Callable[[], None] | None = None):
        super().__init__(parent)
        self.saat_master_berubah = saat_master_berubah
        tab = ttk.Notebook(self)
        tab.pack(fill="both", expand=True, padx=8, pady=8)
        self.sub_tab: list[PanelCrud] = []
        for judul, kelas in (("Jenis", SubTabJenis), ("Varietas", SubTabVarietas),
                             ("Pohon", SubTabPohon), ("Keterangan", SubTabKeterangan)):
            halaman = kelas(tab, service, self._saat_berubah)
            tab.add(halaman, text=judul)
            self.sub_tab.append(halaman)

    def _saat_berubah(self) -> None:
        for halaman in self.sub_tab:
            halaman.muat_ulang()
        if self.saat_master_berubah is not None:
            self.saat_master_berubah()
