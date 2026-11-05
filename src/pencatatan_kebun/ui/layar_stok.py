"""Layar Stok Pohon: jumlah buah di tiap pohon per periode, beserta sisanya."""
import tkinter as tk
from dataclasses import dataclass
from tkinter import font as tkfont
from tkinter import ttk

from pencatatan_kebun.models import PeriodePanen, Pohon, StokPohon
from pencatatan_kebun.services.exception import InputTidakValidException
from pencatatan_kebun.services.master import MasterService
from pencatatan_kebun.services.periode import PeriodeService
from pencatatan_kebun.services.stok import StokService
from pencatatan_kebun.ui.format import tanggal_ke_tampil, teks_ke_int
from pencatatan_kebun.ui.kalender import EntryTanggal
from pencatatan_kebun.ui.komponen import (
    WARNA_TEKS_NOL,
    BilahRingkasan,
    Catatan,
    ComboObjek,
    PanelCrud,
    baris_bebas,
    baris_isian,
    set_entry,
    wajib_pilih,
)
from pencatatan_kebun.ui.layar_master import (
    id_jenis,
    id_varietas,
    label_jenis,
    label_varietas,
)


@dataclass
class BarisStok:
    """Satu baris tabel: satu pohon, dengan stoknya di periode terpilih (jika ada)."""

    pohon: Pohon
    stok: StokPohon | None = None
    tercatat: int | None = None
    sisa: int | None = None


def label_periode(periode: PeriodePanen) -> str:
    return periode.get_nama() + (" (aktif)" if periode.get_tanggal_selesai() is None else "")


def id_periode(periode: PeriodePanen) -> str:
    return periode.get_id_periode()


class LayarStok(PanelCrud):
    """Tab Stok Pohon.

    Tabel berisi semua pohon (sesuai filter), juga yang belum punya stok di
    periode terpilih (abu-abu), seperti satu baris per pohon di Excel. Pilih
    pohon, isi jumlah buah, tekan Enter: stok tersimpan dan pilihan pindah ke
    pohon berikutnya. Sisa negatif (panen melebihi stok) diberi warna merah.

    Args:
        parent: Widget induk (Notebook jendela utama).
        service: StokService.
        master_service: MasterService, untuk daftar jenis, varietas, pohon.
        periode_service: PeriodeService, untuk daftar periode.
    """

    nama_data = "stok"
    pakai_tombol_baru = False
    # Angka bulat dan tanggal di tengah (panjangnya mirip, enak dibaca).
    kolom = (("Jenis", 100), ("Varietas", 140), ("No.", 50, "center"),
             ("Jumlah buah", 125, "center"), ("Tgl hitung", 130, "center"),
             ("Tercatat", 95, "center"), ("Sisa", 70, "center"))
    teks_kosong = "Belum ada pohon. Daftarkan pohon di tab Data Master."

    def __init__(self, parent: tk.Widget, service: StokService, master_service: MasterService,
                 periode_service: PeriodeService):
        self.master_service = master_service
        self.periode_service = periode_service
        super().__init__(parent, service, self.muat_ulang)
        # Pohon belum dihitung: redup dan miring, sama dengan baris nol di
        # Dashboard (kontras tetap di atas minimum 4,5:1).
        huruf_miring = tkfont.nametofont("TkDefaultFont").copy()
        huruf_miring.configure(slant="italic")
        self.tabel.tree.tag_configure("belum", foreground=WARNA_TEKS_NOL, font=huruf_miring)
        self.tabel.tree.tag_configure("lebih", background="#fde2e1")

        self.total = BilahRingkasan(self)
        self.total.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self._perbarui_total()

    # ---- filter ----

    def buat_filter(self, frame):
        ttk.Label(frame, text="Periode").pack(side="left", padx=(0, 6))
        self.filter_periode = ComboObjek(frame, label_periode, id_periode, width=20)
        self.filter_periode.pack(side="left")
        ttk.Label(frame, text="Jenis").pack(side="left", padx=(12, 6))
        self.filter_jenis = ComboObjek(frame, label_jenis, id_jenis, label_kosong="(Semua)",
                                       width=14)
        self.filter_jenis.pack(side="left")
        ttk.Label(frame, text="Varietas").pack(side="left", padx=(12, 6))
        self.filter_varietas = ComboObjek(frame, lambda v: v.get_nama_varietas(), id_varietas,
                                          label_kosong="(Semua)", width=16)
        self.filter_varietas.pack(side="left")
        self.filter_periode.bind("<<ComboboxSelected>>", lambda _e: self.muat_tabel())
        self.filter_jenis.bind("<<ComboboxSelected>>", lambda _e: self._ganti_filter_jenis())
        self.filter_varietas.bind("<<ComboboxSelected>>", lambda _e: self.muat_tabel())

    def _ganti_filter_jenis(self):
        self._isi_filter_varietas()
        self.muat_tabel()

    def _isi_filter_varietas(self):
        jenis = self.filter_jenis.terpilih()
        self.filter_varietas.isi(self.master_service.daftar_varietas(jenis) if jenis else [])

    def muat_dropdown(self):
        self.filter_periode.isi(self.periode_service.daftar_periode())
        if self.filter_periode.terpilih() is None:
            # Bawaan: periode aktif, atau periode terakhir.
            aktif = self.periode_service.periode_aktif()
            daftar = self.periode_service.daftar_periode()
            if aktif is not None:
                self.filter_periode.pilih_id(aktif.get_id_periode())
            elif daftar:
                self.filter_periode.pilih_id(daftar[-1].get_id_periode())
        self.filter_jenis.isi(self.master_service.daftar_jenis())
        self._isi_filter_varietas()

    # ---- tabel ----

    def data(self):
        periode = self.filter_periode.terpilih()
        if periode is None:
            return []
        varietas = self.filter_varietas.terpilih()
        jenis = self.filter_jenis.terpilih()
        if varietas is not None:
            daftar_pohon = self.master_service.daftar_pohon(varietas)
        else:
            daftar_pohon = self.master_service.daftar_pohon()
            if jenis is not None:
                daftar_pohon = [p for p in daftar_pohon
                                if p.get_varietas().get_jenis().get_id_jenis() == jenis.get_id_jenis()]
        stok = {d["stok"].get_pohon().get_id_pohon(): d
                for d in self.service.daftar_stok_periode(periode.get_id_periode())}
        hasil = []
        for pohon in daftar_pohon:
            d = stok.get(pohon.get_id_pohon())
            if d is None:
                hasil.append(BarisStok(pohon))
            else:
                hasil.append(BarisStok(pohon, d["stok"], d["jumlah_tercatat"], d["sisa"]))
        return hasil

    def muat_tabel(self):
        super().muat_tabel()
        if hasattr(self, "total"):
            self._perbarui_total()

    def _perbarui_total(self):
        if self.filter_periode.terpilih() is None:
            self.total.tampilkan("Belum ada periode. Buka periode di tab Periode Panen.")
            return
        daftar = self.tabel.semua()
        ada = [b for b in daftar if b.stok is not None]
        self.total.tampilkan([
            ("Sudah dihitung", f"{len(ada)} dari {len(daftar)} pohon"),
            ("Jumlah buah", sum(b.stok.get_jumlah_buah() for b in ada)),
            ("Tercatat", sum(b.tercatat for b in ada)),
            ("Sisa", sum(b.sisa for b in ada))])

    def id_objek(self, objek):
        return objek.pohon.get_id_pohon()

    def nilai_baris(self, objek):
        varietas = objek.pohon.get_varietas()
        awal = (varietas.get_jenis().get_nama_jenis(), varietas.get_nama_varietas(),
                objek.pohon.get_nomor_pohon())
        if objek.stok is None:
            return awal + ("-", "-", "-", "-")
        return awal + (objek.stok.get_jumlah_buah(),
                       tanggal_ke_tampil(objek.stok.get_tanggal_hitung()),
                       objek.tercatat, objek.sisa)

    def tag_baris(self, objek):
        if objek.stok is None:
            return ("belum",)
        return ("lebih",) if objek.sisa < 0 else ()

    # ---- form ----

    def buat_form(self, frame):
        self.label_pohon = baris_isian(frame, 0, "Pohon", ttk.Label(frame, style="FormSorot.TLabel"))
        self.entry_jumlah = baris_isian(frame, 1, "Jumlah buah", ttk.Entry(frame, width=10))
        self.tgl_hitung = baris_isian(frame, 2, "Tanggal hitung", EntryTanggal(
            frame, "tanggal_hitung", "Tanggal hitung", sampai_hari_ini=True, tautan=True))
        self.info = Catatan(frame, "Info")
        self.info.grid(row=baris_bebas(frame), column=0, sticky="ew", pady=(16, 0))
        Catatan(frame, "Petunjuk", "Tekan Enter untuk simpan dan lanjut ke pohon berikutnya.").grid(
            row=baris_bebas(frame), column=0, sticky="w", pady=(12, 0))
        self.isian = {"jumlah_buah": self.entry_jumlah, "tanggal_hitung": self.tgl_hitung.entry,
                      "periode_panen": self.filter_periode}

    def teks_judul(self, objek):
        if objek is None:
            return "Pilih pohon di tabel"
        return "Ubah stok" if objek.stok is not None else "Catat stok"

    def saat_mode(self, objek):
        # Hapus hanya untuk pohon yang sudah punya stok.
        ada_stok = objek is not None and objek.stok is not None
        self.tombol_hapus.state(["!disabled"] if ada_stok else ["disabled"])

    def isi_form(self, objek):
        self.label_pohon.configure(text=self._nama_pohon(objek.pohon))
        if objek.stok is None:
            # Tanggal hitung tidak di-reset, supaya mengisi banyak pohon cepat.
            set_entry(self.entry_jumlah, "")
            self.info.tampilkan("Pohon ini belum punya stok di periode ini.")
        else:
            set_entry(self.entry_jumlah, objek.stok.get_jumlah_buah())
            self.tgl_hitung.set_db(objek.stok.get_tanggal_hitung())
            self.info.tampilkan(f"Tercatat {objek.tercatat} buah, sisa {objek.sisa}.")
        self.entry_jumlah.focus_set()
        self.entry_jumlah.select_range(0, "end")

    def kosongkan_form(self):
        self.label_pohon.configure(text="-")
        set_entry(self.entry_jumlah, "")
        self.info.tampilkan("")

    def simpan(self, id_lama):
        if id_lama is None:
            raise InputTidakValidException("Pilih pohon di tabel terlebih dahulu!")
        periode = wajib_pilih(self.filter_periode.terpilih(), "Periode", "periode_panen")
        baris = self.dipilih
        jumlah, tanggal = teks_ke_int(self.entry_jumlah.get()), self.tgl_hitung.get_db()
        if baris.stok is None:
            stok = self.service.catat_stok(baris.pohon, periode, jumlah, tanggal)
        else:
            stok = self.service.ubah_stok(baris.pohon, periode, jumlah, tanggal)
        return BarisStok(baris.pohon, stok)

    def setelah_ubah(self, objek):
        # Lanjut ke pohon berikutnya, seperti turun satu baris di Excel.
        berikut = self.tabel.tree.next(self.id_objek(objek))
        if berikut:
            self.tabel.pilih_id(berikut)

    def setelah_hapus(self, objek):
        """Baris pohon tetap terpilih (sekarang tanpa stok)."""

    def hapus(self, objek):
        periode = wajib_pilih(self.filter_periode.terpilih(), "Periode", "periode_panen")
        self.service.hapus_stok(objek.pohon.get_id_pohon(), periode.get_id_periode())

    def nama(self, objek):
        return f"stok pohon {self._nama_pohon(objek.pohon)}"

    @staticmethod
    def _nama_pohon(pohon: Pohon) -> str:
        return f"{label_varietas(pohon.get_varietas())} nomor {pohon.get_nomor_pohon()}"
