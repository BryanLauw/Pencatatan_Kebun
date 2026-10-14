"""Menu "Cadangan" di jendela utama: simpan cadangan, pulihkan, buka folder otomatis."""
import os
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

from pencatatan_kebun.cadangan import SIMPAN_OTOMATIS, CadanganService, nama_file_bawaan
from pencatatan_kebun.ui.komponen import jalankan_aman

JENIS_FILE = [("Cadangan Pencatatan Kebun", "*.db"), ("Semua file", "*.*")]


class MenuCadangan:
    """Pasang menu "Cadangan" di menubar jendela.

    Args:
        jendela: Jendela utama.
        service: CadanganService.
        setelah_pulihkan: Dipanggil setelah data dipulihkan, untuk memuat ulang
            semua layar.
    """

    def __init__(self, jendela: tk.Tk, service: CadanganService,
                 setelah_pulihkan: Callable[[], None]):
        self.jendela = jendela
        self.service = service
        self.setelah_pulihkan = setelah_pulihkan
        dokumen = Path.home() / "Documents"
        self._folder = dokumen if dokumen.is_dir() else Path.home()

        menubar = tk.Menu(jendela)
        menu = tk.Menu(menubar, tearoff=False)
        menu.add_command(label="Simpan cadangan...", command=self.simpan)
        menu.add_command(label="Pulihkan dari cadangan...", command=self.pulihkan)
        menu.add_separator()
        menu.add_command(label="Buka folder cadangan otomatis", command=self.buka_folder)
        menubar.add_cascade(label="Cadangan", menu=menu)
        jendela.configure(menu=menubar)

    def simpan(self) -> None:
        """Cadangan manual ke file pilihan pengguna, mis. di flashdisk."""
        lokasi = filedialog.asksaveasfilename(
            parent=self.jendela, title="Simpan cadangan data", initialdir=self._folder,
            initialfile=nama_file_bawaan(), defaultextension=".db", filetypes=JENIS_FILE)
        if not lokasi:
            return
        lokasi = Path(lokasi)
        berhasil, _ = jalankan_aman(self.jendela, lambda: self.service.simpan(lokasi))
        if berhasil:
            self._folder = lokasi.parent
            messagebox.showinfo("Cadangan tersimpan",
                                f"Cadangan data tersimpan di:\n{lokasi}\n\nSimpan file ini di "
                                "tempat aman, mis. flashdisk atau Google Drive.",
                                parent=self.jendela)

    def pulihkan(self) -> None:
        """Ganti semua data dengan isi file cadangan, setelah konfirmasi."""
        lokasi = filedialog.askopenfilename(
            parent=self.jendela, title="Pilih file cadangan", initialdir=self._folder,
            filetypes=JENIS_FILE)
        if not lokasi:
            return
        lokasi = Path(lokasi)
        dibuat = datetime.fromtimestamp(lokasi.stat().st_mtime).strftime("%d-%m-%Y %H:%M")
        if not messagebox.askyesno(
                "Pulihkan data",
                f"Semua data sekarang akan diganti dengan isi cadangan:\n{lokasi.name}\n"
                f"(disimpan {dibuat}).\n\nData sekarang disimpan dulu sebagai cadangan "
                "otomatis, jadi masih bisa dikembalikan.\n\nLanjutkan?",
                icon="warning", default="no", parent=self.jendela):
            return
        berhasil, sebelum = jalankan_aman(self.jendela, lambda: self.service.pulihkan(lokasi))
        if berhasil:
            self.setelah_pulihkan()
            messagebox.showinfo("Data dipulihkan",
                                f"Data berhasil dipulihkan dari {lokasi.name}.\n\nData sebelum "
                                f"dipulihkan tersimpan sebagai {sebelum.name} di folder "
                                "cadangan otomatis.", parent=self.jendela)

    def buka_folder(self) -> None:
        """Buka folder cadangan otomatis di File Explorer."""
        folder = self.service.folder_otomatis
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(folder)
        except OSError:
            messagebox.showinfo("Folder cadangan otomatis",
                                f"Cadangan otomatis ({SIMPAN_OTOMATIS} terakhir) ada di:\n{folder}",
                                parent=self.jendela)
