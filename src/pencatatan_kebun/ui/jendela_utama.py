"""Jendela utama aplikasi: satu tab per layar."""
import ctypes
import logging
import tkinter as tk
from tkinter import messagebox, ttk

from pencatatan_kebun.services.master import MasterService
from pencatatan_kebun.services.periode import PeriodeService
from pencatatan_kebun.ui.komponen import PESAN_BUG, atur_gaya
from pencatatan_kebun.ui.layar_master import LayarMaster
from pencatatan_kebun.ui.layar_periode import LayarPeriode

log = logging.getLogger(__name__)


def _aktifkan_dpi() -> None:
    """Minta Windows tidak memperbesar jendela secara bitmap (huruf jadi buram)
    saat skala tampilan di atas 100%. Tidak berpengaruh di sistem lain."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass


class JendelaUtama(tk.Tk):
    """Jendela utama dengan tab untuk tiap layar.

    Layar Stok Pohon, Catat Panen, dan Dashboard ditambahkan bertahap
    sebagai tab baru.

    Args:
        master_service: MasterService untuk layar Data Master.
        periode_service: PeriodeService untuk layar Periode Panen.
    """

    def __init__(self, master_service: MasterService, periode_service: PeriodeService):
        _aktifkan_dpi()
        super().__init__()
        self.title("Pencatatan Kebun")
        # Ukuran dalam piksel layar 100%, dikali skala tampilan Windows (mis. 150%).
        skala = self.winfo_fpixels("1i") / 96
        lebar = min(int(1100 * skala), self.winfo_screenwidth())
        tinggi = min(int(700 * skala), self.winfo_screenheight() - int(80 * skala))
        self.geometry(f"{lebar}x{tinggi}")
        self.minsize(int(900 * skala), int(550 * skala))
        atur_gaya(self)

        self.tab = ttk.Notebook(self)
        self.tab.pack(fill="both", expand=True, padx=8, pady=8)

        self.layar_periode = LayarPeriode(self.tab, periode_service,
                                          saat_berubah=self.saat_periode_berubah)
        self.tab.add(self.layar_periode, text="Periode Panen")

        self.layar_master = LayarMaster(self.tab, master_service,
                                        saat_master_berubah=self.saat_master_berubah)
        self.tab.add(self.layar_master, text="Data Master")

    def saat_master_berubah(self) -> None:
        """Data master berubah: layar lain memuat ulang dropdown-nya (nanti)."""

    def saat_periode_berubah(self) -> None:
        """Periode berubah: layar stok dan dashboard memuat ulang (nanti)."""

    def report_callback_exception(self, exc, val, tb) -> None:
        """Error tak tertangkap di event tkinter: catat ke log, tampilkan pesan umum."""
        log.error("Kesalahan tak terduga di ui", exc_info=(exc, val, tb))
        messagebox.showerror("Gagal", PESAN_BUG, parent=self)
