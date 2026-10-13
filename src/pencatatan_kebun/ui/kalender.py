"""Isian tanggal yang dipilih lewat kalender (tanpa mengetik).

Tanggal di luar batas_awal/batas_akhir tampil abu-abu dan tidak bisa diklik.
"""
import calendar
import tkinter as tk
from collections.abc import Callable
from datetime import date, timedelta
from tkinter import font as tkfont
from tkinter import ttk

from pencatatan_kebun.services.exception import InputTidakValidException
from pencatatan_kebun.ui.format import tanggal_ke_tampil

NAMA_BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
              "Agustus", "September", "Oktober", "November", "Desember"]
NAMA_HARI = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]

WARNA_LATAR = "#ffffff"
WARNA_TERPILIH = "#1f6feb"
WARNA_HARI_INI = "#dbe7ff"
WARNA_NONAKTIF = "#b8b8b8"
WARNA_MINGGU = "#c62828"


# ---- logika (tanpa tkinter, diuji di tests/test_ui_kalender.py) ----

def minggu_bulan(tahun: int, bulan: int) -> list[list[date | None]]:
    """Tanggal satu bulan, dibagi per minggu (Senin-Minggu).

    Returns:
        Daftar minggu; tiap minggu 7 isian, None untuk hari di luar bulan ini.
    """
    return [[date(tahun, bulan, h) if h else None for h in minggu]
            for minggu in calendar.Calendar(firstweekday=0).monthdayscalendar(tahun, bulan)]


def boleh_dipilih(tanggal: date, batas_awal: date | None, batas_akhir: date | None) -> bool:
    """True jika tanggal berada di dalam batas (batas ikut dihitung)."""
    return ((batas_awal is None or tanggal >= batas_awal)
            and (batas_akhir is None or tanggal <= batas_akhir))


def geser_bulan(tahun: int, bulan: int, jumlah: int) -> tuple[int, int]:
    """Maju (jumlah positif) atau mundur sejumlah bulan."""
    indeks = tahun * 12 + (bulan - 1) + jumlah
    return indeks // 12, indeks % 12 + 1


def bulan_bisa_dibuka(tahun: int, bulan: int, batas_awal: date | None,
                      batas_akhir: date | None) -> bool:
    """True jika ada minimal satu tanggal di bulan itu yang boleh dipilih."""
    awal = date(tahun, bulan, 1)
    akhir = date(tahun, bulan, calendar.monthrange(tahun, bulan)[1])
    return ((batas_akhir is None or awal <= batas_akhir)
            and (batas_awal is None or akhir >= batas_awal))


# ---- widget ----

class KalenderPopup(tk.Toplevel):
    """Jendela kecil berisi kalender satu bulan.

    Args:
        pemilik: Widget yang membuka kalender; popup muncul di bawahnya.
        terpilih: Tanggal yang sedang dipilih, atau None.
        batas_awal: Tanggal paling awal yang boleh dipilih, atau None.
        batas_akhir: Tanggal paling akhir yang boleh dipilih, atau None.
        saat_pilih: Dipanggil dengan tanggal yang diklik.
    """

    def __init__(self, pemilik: tk.Widget, terpilih: date | None, batas_awal: date | None,
                 batas_akhir: date | None, saat_pilih: Callable[[date], None]):
        super().__init__(pemilik)
        self.title("Pilih tanggal")
        self.resizable(False, False)
        self.transient(pemilik.winfo_toplevel())
        self.configure(background=WARNA_LATAR)
        self.batas_awal = batas_awal
        self.batas_akhir = batas_akhir
        self.terpilih = terpilih
        self.saat_pilih = saat_pilih

        # Bulan yang dibuka pertama: bulan tanggal terpilih, atau bulan ini,
        # digeser ke dalam batas jika perlu.
        acuan = terpilih or date.today()
        if batas_akhir is not None and acuan > batas_akhir:
            acuan = batas_akhir
        if batas_awal is not None and acuan < batas_awal:
            acuan = batas_awal
        self.tahun, self.bulan = acuan.year, acuan.month

        self.huruf = tkfont.nametofont("TkDefaultFont")
        self.huruf_tebal = self.huruf.copy()
        self.huruf_tebal.configure(weight="bold")

        kepala = tk.Frame(self, background=WARNA_LATAR, padx=8, pady=8)
        kepala.pack(fill="x")
        self.tombol_geser = {}
        for teks, jumlah, sisi in (("«", -12, "left"), ("‹", -1, "left"),
                                   ("»", 12, "right"), ("›", 1, "right")):
            tombol = ttk.Button(kepala, text=teks, width=3,
                                command=lambda j=jumlah: self._geser(j))
            tombol.pack(side=sisi, padx=2)
            self.tombol_geser[jumlah] = tombol
        self.judul = tk.Label(kepala, font=self.huruf_tebal, background=WARNA_LATAR, width=16)
        self.judul.pack(side="left", expand=True)

        self.badan = tk.Frame(self, background=WARNA_LATAR, padx=8)
        self.badan.pack()
        for kolom, nama in enumerate(NAMA_HARI):
            tk.Label(self.badan, text=nama, font=self.huruf_tebal, background=WARNA_LATAR,
                     foreground=WARNA_MINGGU if kolom == 6 else "#333").grid(
                row=0, column=kolom, padx=1, pady=(0, 4))
        self.sel_hari: list[tk.Button] = []
        for baris in range(6):
            for kolom in range(7):
                tombol = tk.Button(self.badan, width=3, relief="flat", font=self.huruf,
                                   cursor="hand2", borderwidth=0, highlightthickness=0)
                tombol.grid(row=baris + 1, column=kolom, padx=1, pady=1, sticky="nsew")
                self.sel_hari.append(tombol)

        kaki = tk.Frame(self, background=WARNA_LATAR, padx=8, pady=8)
        kaki.pack(fill="x")
        hari_ini = date.today()
        self.tombol_hari_ini = ttk.Button(kaki, text="Hari ini",
                                          command=lambda: self._pilih(hari_ini))
        self.tombol_hari_ini.pack(side="left")
        if not boleh_dipilih(hari_ini, batas_awal, batas_akhir):
            self.tombol_hari_ini.state(["disabled"])
        ttk.Button(kaki, text="Batal", command=self.destroy).pack(side="right")

        self.bind("<Escape>", lambda _e: self.destroy())
        self._gambar()
        self._letakkan_di_bawah(pemilik)
        self.grab_set()
        self.focus_set()

    def _letakkan_di_bawah(self, pemilik: tk.Widget) -> None:
        self.update_idletasks()
        x = pemilik.winfo_rootx()
        y = pemilik.winfo_rooty() + pemilik.winfo_height()
        lebar, tinggi = self.winfo_reqwidth(), self.winfo_reqheight()
        x = max(0, min(x, self.winfo_screenwidth() - lebar))
        if y + tinggi > self.winfo_screenheight() - 40:
            y = max(0, pemilik.winfo_rooty() - tinggi)
        self.geometry(f"+{x}+{y}")

    def _geser(self, jumlah: int) -> None:
        self.tahun, self.bulan = geser_bulan(self.tahun, self.bulan, jumlah)
        self._gambar()

    def _gambar(self) -> None:
        self.judul.configure(text=f"{NAMA_BULAN[self.bulan - 1]} {self.tahun}")
        for jumlah, tombol in self.tombol_geser.items():
            tujuan = geser_bulan(self.tahun, self.bulan, jumlah)
            bisa = bulan_bisa_dibuka(*tujuan, self.batas_awal, self.batas_akhir)
            tombol.state(["!disabled"] if bisa else ["disabled"])

        hari_ini = date.today()
        semua = [t for minggu in minggu_bulan(self.tahun, self.bulan) for t in minggu]
        semua += [None] * (len(self.sel_hari) - len(semua))
        for indeks, (tombol, tanggal) in enumerate(zip(self.sel_hari, semua)):
            if tanggal is None:
                # Hari di luar bulan ini tidak ditampilkan.
                tombol.configure(text="", state="disabled", background=WARNA_LATAR,
                                 cursor="arrow", command="")
                continue
            aktif = boleh_dipilih(tanggal, self.batas_awal, self.batas_akhir)
            dipilih = tanggal == self.terpilih
            warna_teks = WARNA_MINGGU if indeks % 7 == 6 else "#111"
            tombol.configure(
                text=str(tanggal.day),
                state="normal" if aktif else "disabled",
                cursor="hand2" if aktif else "arrow",
                background=(WARNA_TERPILIH if dipilih
                            else WARNA_HARI_INI if tanggal == hari_ini else WARNA_LATAR),
                foreground="#fff" if dipilih else warna_teks,
                activebackground="#d6e4ff",
                disabledforeground=WARNA_NONAKTIF,
                font=self.huruf_tebal if tanggal == hari_ini or dipilih else self.huruf,
                command=(lambda t=tanggal: self._pilih(t)) if aktif else "",
            )

    def _pilih(self, tanggal: date) -> None:
        self.destroy()
        self.saat_pilih(tanggal)


class EntryTanggal(ttk.Frame):
    """Isian tanggal: tampil DD-MM-YYYY, diisi dengan memilih di kalender.

    Klik isian (atau tekan panah bawah) untuk membuka kalender. Tanggal tidak
    bisa diketik, jadi selalu valid; batas_awal/batas_akhir memblok tanggal
    yang tidak boleh dipilih.

    Args:
        parent: Widget induk.
        kolom: Nama kolom untuk exception, mis. "tanggal_mulai", agar isian
            ini yang disorot saat service menolak tanggalnya.
        label: Nama isian untuk pesan, mis. "Tanggal mulai".
        hari_ini: Jika True, langsung diisi tanggal hari ini.
        boleh_kosong: Jika True, ada tombol "Kosongkan" dan get_db boleh
            mengembalikan None (mis. tanggal selesai periode).
        batas_awal: Tanggal paling awal yang boleh dipilih, atau None.
        batas_akhir: Tanggal paling akhir yang boleh dipilih, atau None
            (mis. date.today() untuk tanggal panen).
        saat_berubah: Dipanggil dengan tanggal baru (atau None) setiap kali
            isinya berubah, termasuk lewat set_db.
    """

    def __init__(self, parent: tk.Widget, kolom: str, label: str = "Tanggal",
                 hari_ini: bool = True, boleh_kosong: bool = False,
                 batas_awal: date | None = None, batas_akhir: date | None = None,
                 saat_berubah: Callable[[date | None], None] | None = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.kolom = kolom
        self.label = label
        self.boleh_kosong = boleh_kosong
        self.batas_awal = batas_awal
        self.batas_akhir = batas_akhir
        self.saat_berubah = saat_berubah
        self._tanggal: date | None = None
        self.popup: KalenderPopup | None = None

        # Combobox readonly dipakai supaya tampilannya seperti dropdown biasa;
        # daftar bawaannya diganti kalender.
        self.entry = ttk.Combobox(self, state="readonly", width=11, values=[])
        self.entry.pack(side="left")
        self.entry.bind("<Button-1>", self._klik)
        self.entry.bind("<Down>", self._klik)

        self.tombol_hari_ini = ttk.Button(self, text="Hari ini", command=self.isi_hari_ini)
        self.tombol_hari_ini.pack(side="left", padx=(6, 0))
        if boleh_kosong:
            ttk.Button(self, text="Kosongkan", command=lambda: self._set(None)).pack(
                side="left", padx=(6, 0))
        self._perbarui_tombol()
        if hari_ini:
            self.isi_hari_ini()

    def _klik(self, _event) -> str:
        self.entry.focus_set()
        if self.popup is None or not self.popup.winfo_exists():
            self.popup = KalenderPopup(self.entry, self._tanggal, self.batas_awal,
                                       self.batas_akhir, self._set)
        return "break"  # jangan buka daftar bawaan combobox

    def _set(self, tanggal: date | None) -> None:
        self._tanggal = tanggal
        self.entry.set(tanggal_ke_tampil(tanggal.isoformat()) if tanggal else "")
        if self.saat_berubah is not None:
            self.saat_berubah(tanggal)

    def _perbarui_tombol(self) -> None:
        bisa = boleh_dipilih(date.today(), self.batas_awal, self.batas_akhir)
        self.tombol_hari_ini.state(["!disabled"] if bisa else ["disabled"])

    def set_batas(self, batas_awal: date | None = None, batas_akhir: date | None = None) -> None:
        """Ganti batas tanggal yang boleh dipilih.

        Tanggal yang sudah terisi tidak diubah walaupun di luar batas baru;
        service yang akan menolaknya saat disimpan.
        """
        self.batas_awal = batas_awal
        self.batas_akhir = batas_akhir
        self._perbarui_tombol()

    def isi_hari_ini(self) -> None:
        self._set(date.today())

    def kosongkan(self) -> None:
        self._set(None)

    def get(self) -> date | None:
        """Tanggal terpilih sebagai objek date, atau None."""
        return self._tanggal

    def get_db(self) -> str | None:
        """Tanggal YYYY-MM-DD untuk service, atau None jika kosong.

        Raises:
            InputTidakValidException: Kosong padahal boleh_kosong False.
        """
        if self._tanggal is None:
            if self.boleh_kosong:
                return None
            raise InputTidakValidException(f"{self.label} wajib dipilih!", kolom=self.kolom)
        return self._tanggal.isoformat()

    def set_db(self, teks_db: str | None) -> None:
        """Isi dari tanggal YYYY-MM-DD model (None = kosong)."""
        self._set(date.fromisoformat(teks_db) if teks_db else None)


def sehari_setelah(tanggal: date | None) -> date | None:
    """Tanggal berikutnya, atau None. Untuk batas tanggal selesai > tanggal mulai."""
    return tanggal + timedelta(days=1) if tanggal else None
