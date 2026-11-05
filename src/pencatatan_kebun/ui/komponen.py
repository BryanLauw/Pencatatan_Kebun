"""Komponen tkinter yang dipakai bersama oleh semua layar."""
import logging
import tkinter as tk
from collections.abc import Callable, Iterable, Sequence
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from pencatatan_kebun.services.exception import (
    InputTidakValidException,
    ServiceException,
)
from pencatatan_kebun.ui.format import kalimat

log = logging.getLogger(__name__)

UKURAN_HURUF = 12

# Palet terang dengan aksen hijau kebun. Ubah di sini untuk mengganti tampilan.
WARNA_LATAR = "#f5f8f3"        # latar jendela
WARNA_PERMUKAAN = "#ffffff"    # isian, tabel, kartu
WARNA_GARIS = "#d8e0d4"        # garis tipis di sekeliling isian dan kartu
WARNA_TAB = "#e6ede2"          # tab yang tidak dipilih
WARNA_HIJAU = "#2f7d4f"        # aksen utama (tombol utama, pilihan, fokus)
WARNA_HIJAU_TUA = "#245f3d"    # judul, tombol utama saat disorot
WARNA_HIJAU_MUDA = "#e1f0e4"   # sorotan lembut (hover, judul kolom, baris aktif)
WARNA_TEKS = "#1f2a22"
WARNA_TEKS_REDUP = "#5d6b61"
# Baris tanpa nilai (mis. keterangan 0 buah), dipakai bersama huruf miring.
# Kontras 4,7:1 di atas putih (minimum WCAG 4,5:1); jangan dibuat lebih pucat.
WARNA_TEKS_NOL = "#6b7670"
WARNA_PILIHAN = "#cde6d3"      # baris tabel terpilih (teks tetap gelap)
WARNA_SALAH = "#ffd6d6"
PESAN_BUG = ("Terjadi kesalahan tak terduga. Silakan coba lagi.\n"
             "Jika terus terjadi, beri tahu pembuat aplikasi.")


def skala(widget: tk.Widget, piksel: int) -> int:
    """Ubah ukuran piksel untuk layar 100% menjadi piksel layar sebenarnya
    (mis. 380 -> 570 pada skala tampilan Windows 150%)."""
    return int(piksel * widget.winfo_fpixels("1i") / 96)


def atur_gaya(root: tk.Tk) -> None:
    """Atur tema, huruf besar, dan tinggi baris tabel untuk seluruh aplikasi.

    Args:
        root: Jendela utama.
    """
    gaya = ttk.Style(root)
    # clam dipakai karena warna isian, tombol, dan tab bisa diubah penuh.
    gaya.theme_use("clam")

    for nama in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(nama).configure(size=UKURAN_HURUF)
    huruf = tkfont.nametofont("TkDefaultFont")
    keluarga = huruf.actual("family")
    root.configure(background=WARNA_LATAR)
    root.option_add("*TCombobox*Listbox.font", huruf)
    root.option_add("*TCombobox*Listbox.background", WARNA_PERMUKAAN)
    root.option_add("*TCombobox*Listbox.foreground", WARNA_TEKS)
    root.option_add("*TCombobox*Listbox.selectBackground", WARNA_HIJAU)
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    root.option_add("*Menu.font", huruf)

    # Dasar: semua widget ttk mewarisi dari ".".
    gaya.configure(".", background=WARNA_LATAR, foreground=WARNA_TEKS, bordercolor=WARNA_GARIS,
                   lightcolor=WARNA_LATAR, darkcolor=WARNA_LATAR, troughcolor=WARNA_LATAR,
                   focuscolor=WARNA_HIJAU, selectbackground=WARNA_HIJAU,
                   selectforeground="#ffffff")
    gaya.map(".", foreground=[("disabled", "#9aa69d")])

    # Tombol: putih dengan garis tipis; "Utama" hijau penuh untuk aksi utama (Simpan).
    # Padding vertikal 4: tinggi tombol sama dengan isian dan dropdown, jadi
    # sejajar bila berada di satu baris (mis. "Hari ini" di samping tanggal).
    # width -8: lebar minimum 8 huruf (bawaan clam 11), supaya tombol pendek
    # seperti "Simpan" tidak memakan tempat dan bilah aksi tetap lega.
    gaya.configure("TButton", padding=(14, 4), width=-8, background=WARNA_PERMUKAAN,
                   bordercolor="#a9bba5", lightcolor=WARNA_PERMUKAAN, darkcolor="#c9d6c5")
    gaya.map("TButton",
             background=[("disabled", WARNA_LATAR), ("pressed", "#cfe5d4"),
                         ("active", WARNA_HIJAU_MUDA)],
             bordercolor=[("focus", WARNA_HIJAU)])
    gaya.configure("Utama.TButton", background=WARNA_HIJAU, foreground="#ffffff",
                   bordercolor=WARNA_HIJAU, lightcolor=WARNA_HIJAU, darkcolor=WARNA_HIJAU)
    gaya.map("Utama.TButton",
             background=[("disabled", "#a9c8b4"), ("pressed", WARNA_HIJAU_TUA),
                         ("active", WARNA_HIJAU_TUA)],
             foreground=[("disabled", "#ffffff")],
             bordercolor=[("disabled", "#a9c8b4"), ("active", WARNA_HIJAU_TUA)],
             lightcolor=[("active", WARNA_HIJAU_TUA)], darkcolor=[("active", WARNA_HIJAU_TUA)])

    # Isian: putih, garis tipis, garis hijau saat difokus.
    for kelas in ("TEntry", "TCombobox", "TSpinbox"):
        gaya.configure(kelas, fieldbackground=WARNA_PERMUKAAN, padding=(6, 5),
                       bordercolor=WARNA_GARIS, lightcolor=WARNA_GARIS, darkcolor=WARNA_GARIS)
        gaya.map(kelas, bordercolor=[("focus", WARNA_HIJAU)],
                 lightcolor=[("focus", WARNA_HIJAU)], darkcolor=[("focus", WARNA_HIJAU)])
    gaya.configure("TCombobox", background=WARNA_PERMUKAAN, arrowcolor=WARNA_TEKS_REDUP)
    # clam memberi teks putih pada dropdown yang difokus (aslinya latar biru);
    # latar kita putih, jadi teks dipaksa gelap supaya tidak hilang.
    gaya.map("TCombobox", fieldbackground=[("readonly", WARNA_PERMUKAAN)],
             foreground=[("readonly", "focus", WARNA_TEKS)],
             selectbackground=[("readonly", WARNA_PERMUKAAN)],
             selectforeground=[("readonly", WARNA_TEKS)],
             background=[("active", WARNA_HIJAU_MUDA)])

    # Tab: tab terpilih menyatu dengan isi halaman.
    gaya.configure("TNotebook", tabmargins=(0, 4, 0, 0), borderwidth=0)
    gaya.configure("TNotebook.Tab", padding=(18, 8), background=WARNA_TAB,
                   foreground=WARNA_TEKS_REDUP, lightcolor=WARNA_TAB, bordercolor=WARNA_GARIS)
    gaya.map("TNotebook.Tab",
             padding=[("selected", (18, 8, 18, 8))],  # clam memberi tab terpilih padding khusus
             background=[("selected", WARNA_LATAR), ("active", WARNA_HIJAU_MUDA)],
             foreground=[("selected", WARNA_HIJAU_TUA)],
             lightcolor=[("selected", WARNA_LATAR)])

    # Tab tingkat kedua (mis. jenis di Dashboard): pil, supaya jelas berada di
    # bawah tab utama. Pil tidak terpilih putih bergaris tipis (tetap terlihat
    # bisa diklik); pil terpilih hijau muda bergaris hijau, teks tebal.
    gaya.configure("Pil.TNotebook", tabmargins=(0, 0, 0, 8), borderwidth=0,
                   bordercolor=WARNA_LATAR, lightcolor=WARNA_LATAR, darkcolor=WARNA_LATAR)
    gaya.configure("Pil.TNotebook.Tab", padding=(16, 5), background=WARNA_PERMUKAAN,
                   foreground=WARNA_TEKS_REDUP, bordercolor=WARNA_GARIS,
                   lightcolor=WARNA_PERMUKAAN, darkcolor=WARNA_PERMUKAAN)
    gaya.map("Pil.TNotebook.Tab",
             padding=[("selected", (16, 5))],
             background=[("selected", WARNA_HIJAU_MUDA), ("active", "#f0f6ee")],
             foreground=[("selected", WARNA_HIJAU_TUA), ("active", WARNA_TEKS)],
             bordercolor=[("selected", "#9cc7a8")],
             lightcolor=[("selected", WARNA_HIJAU_MUDA), ("active", "#f0f6ee")],
             darkcolor=[("selected", WARNA_HIJAU_MUDA), ("active", "#f0f6ee")],
             font=[("selected", (keluarga, UKURAN_HURUF, "bold"))])

    # Tabel: baris lega, judul kolom hijau muda, baris terpilih hijau lembut
    # dengan teks tetap gelap (blok hijau tua terlalu menarik mata).
    gaya.configure("Treeview", rowheight=huruf.metrics("linespace") + 12,
                   background=WARNA_PERMUKAAN, fieldbackground=WARNA_PERMUKAAN,
                   bordercolor=WARNA_GARIS, lightcolor=WARNA_PERMUKAAN,
                   darkcolor=WARNA_PERMUKAAN)
    gaya.map("Treeview", background=[("selected", WARNA_PILIHAN)],
             foreground=[("selected", WARNA_TEKS)])
    gaya.configure("Treeview.Heading", font=(keluarga, UKURAN_HURUF, "bold"), padding=(8, 7),
                   background=WARNA_HIJAU_MUDA, foreground=WARNA_HIJAU_TUA, relief="flat",
                   bordercolor=WARNA_GARIS, lightcolor=WARNA_HIJAU_MUDA,
                   darkcolor=WARNA_HIJAU_MUDA)
    gaya.map("Treeview.Heading", background=[("active", "#cfe5d4")])

    gaya.configure("TScrollbar", background="#c4d0c0", troughcolor=WARNA_LATAR,
                   bordercolor=WARNA_LATAR, lightcolor="#c4d0c0", darkcolor="#c4d0c0",
                   arrowcolor=WARNA_TEKS_REDUP, relief="flat")
    gaya.map("TScrollbar", background=[("active", "#a3b59f")])

    gaya.configure("TSeparator", background=WARNA_GARIS)
    for kelas in ("TCheckbutton", "TRadiobutton"):
        gaya.configure(kelas, indicatorbackground=WARNA_PERMUKAAN)
        gaya.map(kelas, indicatorbackground=[("selected", WARNA_HIJAU)],
                 background=[("active", WARNA_LATAR)])
    gaya.configure("TLabelframe", bordercolor=WARNA_GARIS)
    gaya.configure("TLabelframe.Label", foreground=WARNA_HIJAU_TUA,
                   font=(keluarga, UKURAN_HURUF, "bold"))

    gaya.configure("Judul.TLabel", font=(keluarga, UKURAN_HURUF + 2, "bold"),
                   foreground=WARNA_HIJAU_TUA)

    # Kartu putih di Dashboard (ringkasan angka dan pie).
    gaya.configure("Kartu.TFrame", background=WARNA_PERMUKAAN, relief="solid", borderwidth=1,
                   bordercolor=WARNA_GARIS)
    gaya.configure("Kartu.TLabel", background=WARNA_PERMUKAAN, foreground=WARNA_TEKS_REDUP)
    gaya.configure("KartuJudul.TLabel", background=WARNA_PERMUKAAN, foreground=WARNA_TEKS,
                   font=(keluarga, UKURAN_HURUF, "bold"))
    gaya.configure("KartuAngka.TLabel", background=WARNA_PERMUKAAN, foreground=WARNA_HIJAU_TUA,
                   font=(keluarga, UKURAN_HURUF + 10, "bold"))

    # Tautan: tombol tanpa bingkai bertulisan hijau, untuk aksi ringan di dalam kartu.
    gaya.configure("Tautan.TButton", background=WARNA_PERMUKAAN, foreground=WARNA_HIJAU,
                   bordercolor=WARNA_PERMUKAAN, lightcolor=WARNA_PERMUKAAN,
                   darkcolor=WARNA_PERMUKAAN, padding=(8, 3))
    gaya.map("Tautan.TButton",
             background=[("pressed", "#cfe5d4"), ("active", WARNA_HIJAU_MUDA)],
             foreground=[("active", WARNA_HIJAU_TUA)],
             bordercolor=[("active", WARNA_HIJAU_MUDA)],
             lightcolor=[("active", WARNA_HIJAU_MUDA)], darkcolor=[("active", WARNA_HIJAU_MUDA)])
    # Tautan kecil di baris label isian: tanpa padding (rata dengan tepi kanan
    # isian di bawahnya) dan tanpa latar saat disorot, hanya teks menggelap.
    gaya.configure("TautanKecil.TButton", background=WARNA_PERMUKAAN, foreground=WARNA_HIJAU,
                   bordercolor=WARNA_PERMUKAAN, lightcolor=WARNA_PERMUKAAN,
                   darkcolor=WARNA_PERMUKAAN, padding=0, width=0)
    gaya.map("TautanKecil.TButton",
             background=[("active", WARNA_PERMUKAAN)],
             foreground=[("disabled", "#9aa69d"), ("active", WARNA_HIJAU_TUA)],
             bordercolor=[("active", WARNA_PERMUKAAN), ("focus", WARNA_PERMUKAAN)],
             lightcolor=[("active", WARNA_PERMUKAAN)], darkcolor=[("active", WARNA_PERMUKAAN)])

    gaya.configure("Salah.TEntry", fieldbackground=WARNA_SALAH)
    gaya.map("Salah.TCombobox", fieldbackground=[("readonly", WARNA_SALAH)])

    # Panel form (kartu putih di kanan layar data). Widget di dalamnya diberi
    # gaya Form.* oleh ke_kartu(), supaya latarnya ikut putih.
    gaya.configure("Form.TFrame", background=WARNA_PERMUKAAN)
    gaya.configure("Form.TLabel", background=WARNA_PERMUKAAN, foreground=WARNA_TEKS)
    # Label isian semibold (lebih ringan dari tebal, seperti form web); jika
    # huruf Semibold tidak ada di komputer itu, pakai tebal biasa.
    semibold = ((f"{keluarga} Semibold", UKURAN_HURUF)
                if f"{keluarga} Semibold" in tkfont.families(root)
                else (keluarga, UKURAN_HURUF, "bold"))
    gaya.configure("FormLabel.TLabel", background=WARNA_PERMUKAAN, foreground=WARNA_TEKS,
                   font=semibold)
    gaya.configure("FormJudul.TLabel", background=WARNA_PERMUKAAN, foreground=WARNA_HIJAU_TUA,
                   font=(keluarga, UKURAN_HURUF + 4, "bold"))
    # Nilai yang disorot di form (mis. nama pohon di Stok): menonjol, tetapi di
    # bawah judul panel.
    gaya.configure("FormSorot.TLabel", background=WARNA_PERMUKAAN, foreground=WARNA_TEKS,
                   font=(keluarga, UKURAN_HURUF + 1, "bold"))
    gaya.configure("Form.TSeparator", background=WARNA_GARIS)

    # Callout: kotak pesan berlatar lembut, seperti "alert" di halaman web.
    for nama, latar, teks in (("Info", "#eef5ec", WARNA_TEKS),
                              ("Peringatan", "#fff4dc", "#6b4a00"),
                              ("Sukses", "#e3f2e6", WARNA_HIJAU_TUA)):
        gaya.configure(f"{nama}.TLabel", background=latar, foreground=teks, padding=(12, 8))
    gaya.configure("Petunjuk.TLabel", background=WARNA_PERMUKAAN, foreground=WARNA_TEKS_REDUP)

    # Tombol bahaya (Hapus): putih, teks dan garis merah; merah muda saat disorot.
    gaya.configure("Bahaya.TButton", foreground="#b42318", bordercolor="#e3aaa5")
    gaya.map("Bahaya.TButton",
             background=[("disabled", WARNA_PERMUKAAN), ("pressed", "#f9d7d3"),
                         ("active", "#fdecea")],
             bordercolor=[("disabled", WARNA_GARIS), ("focus", "#b42318")],
             foreground=[("disabled", "#9aa69d")])

    # Bilah ringkasan di bawah tabel: label redup, angka tebal.
    gaya.configure("Ringkasan.TFrame", background=WARNA_PERMUKAAN, relief="solid",
                   borderwidth=1, bordercolor=WARNA_GARIS)
    gaya.configure("RingkasanLabel.TLabel", background=WARNA_PERMUKAAN,
                   foreground=WARNA_TEKS_REDUP)
    gaya.configure("RingkasanAngka.TLabel", background=WARNA_PERMUKAAN, foreground=WARNA_TEKS,
                   font=(keluarga, UKURAN_HURUF, "bold"))

    # Pesan di tengah tabel kosong (empty state).
    gaya.configure("Kosong.TLabel", background=WARNA_PERMUKAAN, foreground=WARNA_TEKS_REDUP,
                   justify="center")


# Gaya widget di luar kartu -> gayanya di dalam kartu form (lihat ke_kartu).
_GAYA_KARTU = {("TLabel", ""): "Form.TLabel", ("TLabel", "Judul.TLabel"): "FormJudul.TLabel",
               ("TFrame", ""): "Form.TFrame", ("TSeparator", ""): "Form.TSeparator"}


def ke_kartu(widget: tk.Widget) -> None:
    """Beri latar putih pada label dan frame di dalam kartu form, sampai ke
    dalam frame (mis. EntryTanggal). Gaya ttk berlaku per kelas, bukan per
    wadah, jadi tanpa ini label di kartu putih berlatar abu.

    Label dengan gaya khusus (mis. callout Info.TLabel) tidak diubah.
    """
    for anak in widget.winfo_children():
        kelas = anak.winfo_class()
        try:
            gaya = str(anak.cget("style"))
        except tk.TclError:
            gaya = None
        if gaya is not None and (kelas, gaya) in _GAYA_KARTU:
            anak.configure(style=_GAYA_KARTU[(kelas, gaya)])
        ke_kartu(anak)


class Catatan(ttk.Label):
    """Teks di form yang hanya tampil bila berisi: petunjuk, info, peringatan,
    atau pesan sukses (lihat gaya callout di atur_gaya).

    Callout berlatar warna; tanpa disembunyikan, callout kosong tampil sebagai
    kotak berwarna tanpa isi. Letakkan dengan grid() atau pack() seperti biasa,
    lalu ubah isinya dengan tampilkan().

    Args:
        parent: Widget induk.
        jenis: "Petunjuk", "Info", "Peringatan", atau "Sukses".
        teks: Isi awal; kosong berarti tersembunyi.
        lebar: Lebar baris maksimum dalam piksel layar 100%.
    """

    def __init__(self, parent: tk.Widget, jenis: str = "Info", teks: str = "", lebar: int = 360):
        super().__init__(parent, style=f"{jenis}.TLabel", wraplength=skala(parent, lebar),
                         justify="left")
        self._teks_awal = teks
        self._letak: tuple[str, dict] | None = None

    def grid(self, **kwargs) -> None:
        self._letak = ("grid", kwargs)
        self.tampilkan(self._teks_awal)

    def pack(self, **kwargs) -> None:
        self._letak = ("pack", kwargs)
        self.tampilkan(self._teks_awal)

    def tampilkan(self, teks: str) -> None:
        """Ganti isi; teks kosong menyembunyikan catatan."""
        self._teks_awal = teks
        self.configure(text=teks)
        if self._letak is None:
            return
        cara, kwargs = self._letak
        if not teks:
            (super().grid_remove if cara == "grid" else super().pack_forget)()
        else:
            (super().grid if cara == "grid" else super().pack)(**kwargs)


class BarisAlir(ttk.Frame):
    """Wadah yang menyusun anaknya mendatar dan pindah ke baris berikutnya bila
    tidak muat (seperti flex-wrap di web), mis. deretan filter di atas tabel.

    Anak cukup dipasang dengan pack(side="left") seperti biasa; saat wadah
    berubah ukuran, letaknya diatur ulang. Label polos (gaya bawaan) selalu
    ikut baris yang sama dengan widget sesudahnya, supaya label tidak terpisah
    dari isiannya.

    Args:
        parent: Widget induk.
        jarak: Jarak antarkelompok, piksel layar 100%.
        tepi: (kiri-kanan, atas-bawah) jarak isi dari tepi wadah.
    """

    def __init__(self, parent: tk.Widget, jarak: int = 16, tepi: tuple[int, int] = (0, 0),
                 **kwargs):
        super().__init__(parent, **kwargs)
        self._jarak = skala(self, jarak)
        self._jarak_dalam = skala(self, 8)
        self._tepi = (skala(self, tepi[0]), skala(self, tepi[1]))
        self.bind("<Configure>", lambda _e: self.susun())
        self.after_idle(self.susun)

    def _kelompok(self) -> list[list[tk.Widget]]:
        anak = [w for w in self.winfo_children() if w.winfo_manager()]
        hasil: list[list[tk.Widget]] = []
        ikat = False
        for w in anak:
            if ikat:
                hasil[-1].append(w)
            else:
                hasil.append([w])
            gaya = str(w.cget("style")) if w.winfo_class() == "TLabel" else None
            ikat = gaya == ""
        return hasil

    def susun(self) -> None:
        """Atur ulang letak anak sesuai lebar wadah sekarang."""
        if not self.winfo_exists():
            return
        tepi_x, tepi_y = self._tepi
        lebar = self.winfo_width() - 2 * tepi_x
        if lebar <= 1:
            return
        x = y = tinggi_baris = 0
        for kelompok in self._kelompok():
            lebar_k = (sum(w.winfo_reqwidth() for w in kelompok)
                       + self._jarak_dalam * (len(kelompok) - 1))
            tinggi_k = max(w.winfo_reqheight() for w in kelompok)
            if x > 0 and x + lebar_k > lebar:
                x, y, tinggi_baris = 0, y + tinggi_baris + skala(self, 8), 0
            for w in kelompok:
                w.place(x=tepi_x + x, y=tepi_y + y + (tinggi_k - w.winfo_reqheight()) // 2)
                x += w.winfo_reqwidth() + self._jarak_dalam
            x += self._jarak - self._jarak_dalam
            tinggi_baris = max(tinggi_baris, tinggi_k)
        tinggi = y + tinggi_baris + 2 * tepi_y
        if int(self.cget("height")) != tinggi:
            self.configure(height=tinggi)


class BilahRingkasan(BarisAlir):
    """Bilah putih berisi pasangan label redup dan angka tebal, mis.
    "Buah 11 · Total bobot 18,50 kg", untuk ringkasan di bawah tabel. Pasangan
    yang tidak muat pindah ke baris berikutnya."""

    def __init__(self, parent: tk.Widget):
        super().__init__(parent, jarak=28, tepi=(14, 8), style="Ringkasan.TFrame")

    def tampilkan(self, isi: Sequence[tuple[str, object]] | str) -> None:
        """Ganti isi bilah.

        Args:
            isi: Daftar (label, nilai), atau satu kalimat (mis. saat data kosong).
        """
        for anak in self.winfo_children():
            anak.destroy()
        if isinstance(isi, str):
            ttk.Label(self, text=isi, style="RingkasanLabel.TLabel").pack(side="left")
        else:
            for label, nilai in isi:
                # Pasangan dalam satu frame supaya label dan angkanya tidak terpisah baris.
                pasangan = ttk.Frame(self, style="Form.TFrame")
                ttk.Label(pasangan, text=label, style="RingkasanLabel.TLabel").pack(
                    side="left", padx=(0, 6))
                ttk.Label(pasangan, text=str(nilai), style="RingkasanAngka.TLabel").pack(
                    side="left")
                pasangan.pack(side="left")
        self.after_idle(self.susun)


# ---- pesan dan penanganan error ----

class Dibatalkan(Exception):
    """Pengguna memilih "Tidak" di dialog konfirmasi (mis. peringatan sisa
    buah). jalankan_aman menghentikan proses tanpa pesan error."""


def _tandai_salah(widget: tk.Widget | None) -> None:
    """Beri warna latar merah muda pada isian yang salah, lalu fokus ke sana."""
    if widget is None:
        return
    kelas = widget.winfo_class()
    if kelas in ("TEntry", "TCombobox"):
        widget.configure(style=f"Salah.{kelas}")
    widget.focus_set()


def _hapus_tanda(isian: Iterable[tk.Widget]) -> None:
    """Kembalikan warna isian ke normal."""
    for widget in isian:
        if widget.winfo_class() in ("TEntry", "TCombobox"):
            widget.configure(style="")


def tampilkan_salah(parent: tk.Widget, pesan: str, widget: tk.Widget | None = None) -> None:
    """Tampilkan pesan kesalahan dan sorot isian terkait.

    Args:
        parent: Widget pemilik dialog.
        pesan: Kalimat untuk pengguna.
        widget: Isian yang salah, jika ada.
    """
    messagebox.showerror("Gagal", pesan, parent=parent)
    _tandai_salah(widget)


def jalankan_aman(parent: tk.Widget, fungsi: Callable[[], object],
                  isian: dict[str, tk.Widget] | None = None) -> tuple[bool, object]:
    """Panggil fungsi service dan tampilkan pesan jika gagal.

    ServiceException ditampilkan dengan e.pesan, dan isian e.kolom disorot.
    Dibatalkan menghentikan proses tanpa pesan. Exception lain dianggap bug:
    dicatat ke log dan ditampilkan pesan umum.

    Args:
        parent: Widget pemilik dialog pesan.
        fungsi: Fungsi tanpa argumen, mis. lambda: service.tambah_jenis(nama).
        isian: Peta nama kolom exception -> widget isian, mis.
            {"nama_jenis": entry_nama}.

    Returns:
        (True, hasil fungsi) jika berhasil, (False, None) jika gagal atau
        dibatalkan.
    """
    isian = isian or {}
    _hapus_tanda(isian.values())
    try:
        return True, fungsi()
    except Dibatalkan:
        pass
    except ServiceException as e:
        tampilkan_salah(parent, e.pesan, isian.get(e.kolom))
    except Exception:
        log.exception("Kesalahan tak terduga")
        messagebox.showerror("Gagal", PESAN_BUG, parent=parent)
    return False, None


def konfirmasi_hapus(parent: tk.Widget, nama: str) -> bool:
    """Tanya pengguna sebelum menghapus.

    Args:
        parent: Widget pemilik dialog.
        nama: Data yang akan dihapus, mis. "jenis Durian".

    Returns:
        True jika pengguna memilih Ya.
    """
    return messagebox.askyesno(
        "Hapus data", f"Yakin ingin menghapus {nama}?\nData yang dihapus tidak bisa dikembalikan.",
        icon="warning", default="no", parent=parent)


# ---- isian ----

class ComboObjek(ttk.Combobox):
    """Dropdown (hanya pilih, tidak bisa diketik) yang berisi objek model.

    Yang tampil adalah label tiap objek, tetapi terpilih() mengembalikan
    objeknya. Saat diisi ulang, pilihan sebelumnya dipertahankan jika objek
    dengan id yang sama masih ada.

    Args:
        parent: Widget induk.
        label_fn: Fungsi objek -> teks yang ditampilkan.
        id_fn: Fungsi objek -> id, untuk mempertahankan pilihan.
        label_kosong: Jika diisi, ditambahkan pilihan pertama dengan label
            ini yang berarti None (mis. "(Semua jenis)" untuk filter).
    """

    def __init__(self, parent: tk.Widget, label_fn: Callable[[object], str],
                 id_fn: Callable[[object], str], label_kosong: str | None = None, **kwargs):
        kwargs.setdefault("width", 25)
        super().__init__(parent, state="readonly", **kwargs)
        self.label_fn = label_fn
        self.id_fn = id_fn
        self.label_kosong = label_kosong
        self._objek: list[object | None] = []

    def isi(self, daftar: Iterable[object]) -> None:
        """Ganti isi dropdown, pertahankan pilihan jika masih ada."""
        id_lama = self.id_terpilih()
        self._objek = ([None] if self.label_kosong is not None else []) + list(daftar)
        self.configure(values=[self.label_kosong if o is None else self.label_fn(o)
                               for o in self._objek])
        if not self.pilih_id(id_lama):
            self.kosongkan()

    def terpilih(self) -> object | None:
        """Objek yang dipilih, atau None jika belum memilih / memilih label_kosong."""
        i = self.current()
        return self._objek[i] if 0 <= i < len(self._objek) else None

    def id_terpilih(self) -> str | None:
        objek = self.terpilih()
        return self.id_fn(objek) if objek is not None else None

    def pilih_id(self, id_objek: str | None) -> bool:
        """Pilih objek dengan id tertentu.

        Returns:
            True jika objek ditemukan dan dipilih.
        """
        if id_objek is None:
            return False
        for i, objek in enumerate(self._objek):
            if objek is not None and self.id_fn(objek) == id_objek:
                self.current(i)
                return True
        return False

    def kosongkan(self) -> None:
        """Pilih label_kosong jika ada, atau kosongkan pilihan."""
        if self.label_kosong is not None:
            self.current(0)
        else:
            self.set("")


def set_entry(entry: ttk.Entry, teks: object) -> None:
    """Ganti isi Entry."""
    entry.delete(0, "end")
    entry.insert(0, "" if teks is None else str(teks))


# ---- tabel ----

def pas_kolom(tree: ttk.Treeview, kolom: dict[str, int]) -> None:
    """Bagi lebar tabel ke kolom-kolomnya sebanding lebar awal, setiap kali
    ukuran tabel berubah, supaya semua kolom selalu terlihat tanpa gulir ke
    samping.

    Args:
        tree: Treeview yang diatur.
        kolom: Peta id kolom (termasuk "#0" untuk kolom pohon) -> lebar awal
            dalam piksel layar 100%.
    """
    total = sum(kolom.values())
    for nama, lebar in kolom.items():
        tree.column(nama, width=skala(tree, lebar), stretch=False)

    # Lebar minimum tiap kolom: selebar judulnya (isi menyusul lewat
    # perbarui_lebar_minimum), supaya teks tidak terpotong di tabel sempit.
    gaya = ttk.Style(tree)
    huruf_judul = tkfont.Font(font=gaya.lookup("Treeview.Heading", "font") or "TkHeadingFont")
    jarak = skala(tree, 24)
    tree._kolom_judul = {nama: huruf_judul.measure(tree.heading(nama, "text")) + jarak
                         for nama in kolom}
    tree._kolom_min = dict(tree._kolom_judul)

    def sesuaikan(lebar: int) -> None:
        minimum = tree._kolom_min
        # Lebar dari <Configure> termasuk garis tepi tabel; tanpa kelonggaran
        # ini kolom kelebihan beberapa piksel dan gulir mendatar muncul sia-sia.
        lebih = lebar - skala(tree, 4) - sum(minimum.values())
        for nama, bobot in kolom.items():
            # Cukup ruang: minimum + bagian sisa sebanding lebar awal. Kurang
            # ruang: minimum saja, dan tabel bisa digulir ke samping.
            tambahan = lebih * bobot // total if lebih > 0 else 0
            tree.column(nama, width=minimum[nama] + tambahan)

    tree._pas_kolom = lambda: sesuaikan(tree.winfo_width()) if tree.winfo_width() > 1 else None
    tree.bind("<Configure>", lambda e: sesuaikan(e.width), add="+")


def perbarui_lebar_minimum(tree: ttk.Treeview, huruf: tkfont.Font | None = None) -> None:
    """Naikkan lebar minimum kolom (lihat pas_kolom) supaya isi terpanjang
    tiap kolom muat, lalu atur ulang lebar kolom. Panggil setelah tabel diisi."""
    if not hasattr(tree, "_kolom_min"):
        return
    huruf = huruf or tkfont.nametofont("TkDefaultFont")
    jarak = skala(tree, 24)
    kolom = list(tree["columns"])
    lebar = {nama: 0 for nama in kolom}
    for iid in tree.get_children():
        for nama, nilai in zip(kolom, tree.item(iid, "values")):
            lebar[nama] = max(lebar[nama], huruf.measure(str(nilai)))
    for nama in kolom:
        if nama in tree._kolom_judul:
            tree._kolom_min[nama] = max(tree._kolom_judul[nama], lebar[nama] + jarak)
    tree._pas_kolom()


class Tabel(ttk.Frame):
    """Tabel (Treeview) dengan scrollbar yang tiap barisnya mewakili satu objek.

    Args:
        parent: Widget induk.
        kolom: Daftar (judul, lebar) tiap kolom, atau (judul, lebar, "e") untuk
            kolom angka yang rata kanan.
        id_fn: Fungsi objek -> id, dipakai sebagai id baris.
        saat_pilih: Dipanggil dengan objek baris yang dipilih (atau None).
        teks_kosong: Pesan di tengah tabel saat tidak ada baris.
    """

    def __init__(self, parent: tk.Widget, kolom: Sequence[tuple],
                 id_fn: Callable[[object], str],
                 saat_pilih: Callable[[object | None], None] | None = None,
                 teks_kosong: str = "Belum ada data.", **kwargs):
        super().__init__(parent, **kwargs)
        self.id_fn = id_fn
        self.saat_pilih = saat_pilih
        self._objek: dict[str, object] = {}

        nama_kolom = [f"k{i}" for i in range(len(kolom))]
        self.tree = ttk.Treeview(self, columns=nama_kolom, show="headings", selectmode="browse")
        for nama, (judul, _lebar, *rata) in zip(nama_kolom, kolom):
            anchor = rata[0] if rata else "w"
            self.tree.heading(nama, text=judul, anchor=anchor)
            self.tree.column(nama, anchor=anchor)
        pas_kolom(self.tree, {nama: k[1] for nama, k in zip(nama_kolom, kolom)})
        gulir = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=gulir.set)
        # Gulir mendatar hanya tampil bila kolom tidak muat (lihat pas_kolom).
        self._gulir_x = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=self._atur_gulir_x)
        # Scrollbar dipasang dulu supaya tidak terdesak keluar saat ruang sempit.
        gulir.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._saat_pilih)
        # Empty state: pesan di tengah area tabel, ditempel di atas Treeview.
        self.label_kosong = ttk.Label(self.tree, text=teks_kosong, style="Kosong.TLabel",
                                      wraplength=skala(self, 360))

    def atur_teks_kosong(self, teks: str) -> None:
        """Ganti pesan tabel kosong (mis. sesuai filter yang dipilih)."""
        self.label_kosong.configure(text=teks)

    def _atur_gulir_x(self, awal: str, akhir: str) -> None:
        self._gulir_x.set(awal, akhir)
        perlu = float(awal) > 0 or float(akhir) < 1
        if perlu and not self._gulir_x.winfo_ismapped():
            self._gulir_x.pack(side="bottom", fill="x", before=self.tree)
        elif not perlu and self._gulir_x.winfo_ismapped():
            self._gulir_x.pack_forget()

    def isi(self, baris: Iterable[tuple]) -> None:
        """Ganti seluruh isi tabel.

        Args:
            baris: Daftar (objek, nilai tiap kolom) atau (objek, nilai, tag).
                Tag dipakai untuk mewarnai baris, lihat tree.tag_configure.
        """
        self.tree.delete(*self.tree.get_children())
        self._objek.clear()
        for objek, nilai, *tag in baris:
            iid = self.id_fn(objek)
            self._objek[iid] = objek
            self.tree.insert("", "end", iid=iid, values=nilai, tags=tag[0] if tag else ())
        if self._objek:
            self.label_kosong.place_forget()
        else:
            self.label_kosong.place(relx=0.5, rely=0.35, anchor="center")
        perbarui_lebar_minimum(self.tree)

    def semua(self) -> list[object]:
        """Objek semua baris, urut seperti di tabel."""
        return list(self._objek.values())

    def terpilih(self) -> object | None:
        pilihan = self.tree.selection()
        return self._objek.get(pilihan[0]) if pilihan else None

    def pilih_id(self, id_objek: str | None) -> bool:
        """Pilih dan tampilkan baris objek dengan id tertentu.

        Returns:
            True jika barisnya ada.
        """
        if id_objek not in self._objek:
            return False
        self.tree.selection_set(id_objek)
        self.tree.see(id_objek)
        return True

    def lepas_pilihan(self) -> None:
        self.tree.selection_set(())

    def _saat_pilih(self, _event) -> None:
        if self.saat_pilih is not None:
            self.saat_pilih(self.terpilih())


# ---- form ----

def baris_isian(frame: ttk.Frame, baris: int, label: str, widget: tk.Widget) -> tk.Widget:
    """Letakkan label di atas isian (pola form web), satu kolom selebar form.

    Isian teks dan dropdown dibentangkan selebar form, begitu juga widget
    dengan atribut bentang=True (mis. EntryTanggal(tautan=True)); widget lain
    rata kiri. Baris ke-n memakai baris grid
    2n (label) dan 2n+1 (isian); teks tambahan di bawah form diletakkan dengan
    baris_bebas().

    Returns:
        widget, supaya bisa langsung disimpan ke atribut.
    """
    frame.columnconfigure(0, weight=1)
    # Baris label: label di kiri; tautan jalan pintas isian (mis. "Hari ini"
    # pada EntryTanggal) rata kanan, supaya kotak isiannya tetap selebar form.
    kepala = ttk.Frame(frame)
    kepala.grid(row=2 * baris, column=0, sticky="ew", pady=(0 if baris == 0 else 12, 4))
    ttk.Label(kepala, text=label, style="FormLabel.TLabel").pack(side="left")
    if hasattr(widget, "pasang_tautan"):
        widget.pasang_tautan(kepala)
    bentang = (widget.winfo_class() in ("TEntry", "TCombobox")
               or getattr(widget, "bentang", False))
    widget.grid(row=2 * baris + 1, column=0, sticky="ew" if bentang else "w")
    return widget


def baris_bebas(frame: ttk.Frame) -> int:
    """Nomor baris grid kosong berikutnya di form, untuk teks tambahan di
    bawah isian (mis. Catatan).

    Baris yang sudah dibagikan dicatat, karena Catatan yang sedang tersembunyi
    tidak menempati grid; tanpa catatan ini barisnya bisa dibagikan dua kali
    dan isinya bertumpuk saat Catatan muncul.
    """
    baris = max(frame.grid_size()[1], getattr(frame, "_baris_berikut", 0))
    frame._baris_berikut = baris + 1
    return baris


def wajib_pilih(objek, label: str, kolom: str):
    """Tolak jika dropdown belum dipilih (service butuh objek, bukan None).

    Raises:
        InputTidakValidException: objek None, dengan pesan "<label> wajib dipilih!".
    """
    if objek is None:
        raise InputTidakValidException(f"{label} wajib dipilih!", kolom=kolom)
    return objek


def _semua_entry(widget: tk.Widget) -> Iterable[ttk.Entry]:
    """Semua ttk.Entry (termasuk Combobox) di dalam widget, sampai ke dalam frame."""
    for anak in widget.winfo_children():
        if isinstance(anak, ttk.Entry):
            yield anak
        yield from _semua_entry(anak)


class PanelForm(ttk.Frame):
    """Kartu putih panel samping: isi (self.isi) bisa digulir bila tidak muat,
    kaki (self.kaki) selalu terlihat di bawah, seperti panel samping di web
    dengan tombol aksi yang menempel di bawah.

    Gulir muncul hanya bila isi lebih tinggi dari ruang yang ada (mis. layar
    laptop 1366x768), dan bisa dipakai dengan roda mouse di atas panel.
    """

    def __init__(self, parent: tk.Widget):
        # padding 1: isi tidak menutupi garis tepi kartu.
        super().__init__(parent, style="Kartu.TFrame", padding=1)
        # Kaki dipasang lebih dulu supaya saat ruang kurang, isi yang mengecil.
        self.kaki = ttk.Frame(self, style="Form.TFrame", padding=(20, 0, 20, 20))
        self.kaki.pack(side="bottom", fill="x")
        ttk.Separator(self.kaki).pack(fill="x", pady=(0, 16))

        self._kanvas = tk.Canvas(self, background=WARNA_PERMUKAAN, highlightthickness=0,
                                 borderwidth=0)
        self._gulir = ttk.Scrollbar(self, orient="vertical", command=self._kanvas.yview)
        self._kanvas.configure(yscrollcommand=self._atur_gulir)
        self._kanvas.pack(side="left", fill="both", expand=True)
        self.isi = ttk.Frame(self._kanvas, style="Form.TFrame", padding=(20, 20, 20, 20))
        self._jendela = self._kanvas.create_window(0, 0, window=self.isi, anchor="nw")
        self.isi.bind("<Configure>", self._isi_berubah)
        self._kanvas.bind("<Configure>",
                          lambda e: self._kanvas.itemconfigure(self._jendela, width=e.width))
        # Roda mouse: satu pengikat global, aktif hanya bila penunjuk di atas panel ini.
        self.bind_all("<MouseWheel>", self._roda, add="+")

    def _isi_berubah(self, _event) -> None:
        # Kanvas meminta ukuran selebar dan setinggi isi; bila jendela lebih
        # kecil, grid memberi kurang dan gulir muncul.
        self._kanvas.configure(scrollregion=self._kanvas.bbox("all"),
                               width=self.isi.winfo_reqwidth(),
                               height=self.isi.winfo_reqheight())

    def _atur_gulir(self, awal: str, akhir: str) -> None:
        self._gulir.set(awal, akhir)
        perlu = float(awal) > 0 or float(akhir) < 1
        if perlu and not self._gulir.winfo_ismapped():
            self._gulir.pack(side="right", fill="y", before=self._kanvas)
        elif not perlu and self._gulir.winfo_ismapped():
            self._gulir.pack_forget()

    def _roda(self, event) -> None:
        if not self.winfo_exists() or not self._gulir.winfo_ismapped():
            return
        di_bawah = self.winfo_containing(event.x_root, event.y_root)
        if di_bawah is not None and str(di_bawah).startswith(str(self)):
            self._kanvas.yview_scroll(int(-event.delta / 120), "units")


class PanelCrud(ttk.Frame):
    """Pola layar daftar + form: tabel di kiri, form di kanan.

    Klik baris tabel -> form terisi (mode ubah). Tombol "+ Tambah baru" (atau
    Esc) -> form kosong (mode tambah). "Simpan" (atau Enter di isian) memanggil
    simpan(id) dengan id None saat menambah. "+ Tambah baru" dan "Hapus" hanya
    tampil di mode ubah, karena di mode tambah keduanya tidak berguna. Turunan mengisi
    atribut kelas dan menimpa fungsi di bagian "timpa di turunan".

    Args:
        parent: Widget induk.
        service: Service yang dipakai turunan.
        saat_berubah: Dipanggil setelah data tersimpan atau terhapus, agar
            layar lain memuat ulang datanya.
    """

    nama_data = "data"          # untuk judul form, mis. "jenis"
    # (judul, lebar) atau (judul, lebar, "e") untuk kolom angka rata kanan.
    kolom: tuple[tuple, ...] = ()
    # False jika data hanya bisa dipilih dari tabel (tidak ada mode tambah,
    # jadi tidak ada tombol "+ Tambah baru").
    pakai_tombol_baru = True
    teks_kosong = "Belum ada data. Isi form di kanan untuk menambah."

    def __init__(self, parent: tk.Widget, service, saat_berubah: Callable[[], None]):
        super().__init__(parent, padding=12)
        self.service = service
        self.saat_berubah = saat_berubah
        self.dipilih: object | None = None
        # Peta nama kolom exception -> widget isian, untuk menyorot isian salah.
        self.isian: dict[str, tk.Widget] = {}

        self.columnconfigure(0, weight=1)
        # Panel form selebar tetap, tabel mengambil sisa lebar.
        self.columnconfigure(1, minsize=skala(self, 400))
        self.rowconfigure(1, weight=1)

        # Filter yang tidak muat pindah ke baris berikutnya (layar sempit).
        kotak_filter = BarisAlir(self)
        # 16: sama dengan jarak tabel ke panel form, supaya semua jarak antarbagian seragam.
        kotak_filter.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        self.buat_filter(kotak_filter)

        self.tabel = Tabel(self, self.kolom, self.id_objek, saat_pilih=self._saat_pilih,
                           teks_kosong=self.teks_kosong)
        self.tabel.grid(row=1, column=0, sticky="nsew")

        # Panel form: kartu putih setinggi halaman di kanan (pola panel samping web).
        # rowspan 3: turunan boleh memakai baris 2 kolom 0 untuk ringkasan.
        panel = PanelForm(self)
        panel.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=(16, 0))
        kanan = panel.isi
        self.judul_form = ttk.Label(kanan, style="Judul.TLabel")
        self.judul_form.pack(anchor="w", pady=(0, 16))

        form = ttk.Frame(kanan)
        form.pack(fill="x")
        self.buat_form(form)
        for entry in _semua_entry(form):
            entry.bind("<Return>", lambda _e: self._simpan())
            entry.bind("<Escape>", lambda _e: self._ke_tambah())

        # Bilah aksi di kaki panel (selalu terlihat): Simpan (utama) dan
        # "+ Tambah baru" di kiri, Hapus (bahaya) terpisah di kanan supaya tidak
        # tertekan tanpa sengaja. Dua yang terakhir dipasang/dilepas oleh
        # _atur_mode sesuai mode.
        kanan = panel.kaki
        tombol = ttk.Frame(kanan)
        tombol.pack(fill="x")
        self.tombol_simpan = ttk.Button(tombol, text="Simpan", style="Utama.TButton",
                                        command=self._simpan)
        self.tombol_simpan.pack(side="left", padx=(0, 8))
        self.tombol_tambah = (ttk.Button(tombol, text="+ Tambah baru", command=self._ke_tambah)
                              if self.pakai_tombol_baru else None)
        self.tombol_hapus = ttk.Button(tombol, text="Hapus", style="Bahaya.TButton",
                                       command=self._hapus)
        self.buat_tombol(kanan)

        self.status = Catatan(kanan, "Sukses")
        self.status.pack(fill="x", pady=(16, 0))

        ke_kartu(panel)
        self.muat_ulang()
        self.baru()

    # ---- timpa di turunan ----

    def buat_filter(self, frame: ttk.Frame) -> None:
        """Isian filter di atas tabel. Bawaan: tidak ada."""

    def buat_form(self, frame: ttk.Frame) -> None:
        raise NotImplementedError

    def buat_tombol(self, frame: ttk.Frame) -> None:
        """Tombol tambahan di bawah bilah aksi. Bawaan: tidak ada."""

    def muat_dropdown(self) -> None:
        """Isi ulang dropdown filter dan form. Bawaan: tidak ada."""

    def data(self) -> list:
        """Objek yang tampil di tabel (sesuai filter)."""
        raise NotImplementedError

    def id_objek(self, objek) -> str:
        raise NotImplementedError

    def nilai_baris(self, objek) -> tuple:
        raise NotImplementedError

    def tag_baris(self, objek) -> tuple[str, ...]:
        """Tag untuk mewarnai baris. Bawaan: tidak ada."""
        return ()

    def isi_form(self, objek) -> None:
        raise NotImplementedError

    def kosongkan_form(self) -> None:
        raise NotImplementedError

    def simpan(self, id_lama: str | None):
        """Panggil fungsi tambah (id_lama None) atau ubah di service.

        Returns:
            Objek yang tersimpan.
        """
        raise NotImplementedError

    def hapus(self, objek) -> None:
        raise NotImplementedError

    def nama(self, objek) -> str:
        """Nama untuk pesan, mis. "jenis Durian"."""
        raise NotImplementedError

    def teks_judul(self, objek) -> str:
        """Judul di atas form untuk mode tambah (objek None) atau ubah."""
        return f"Tambah {self.nama_data} baru" if objek is None else f"Ubah {self.nama_data}"

    def saat_mode(self, objek) -> None:
        """Setelah mode berganti (objek None = tambah). Bawaan: tidak ada."""

    def setelah_tambah(self, objek) -> None:
        """Setelah tambah berhasil. Bawaan: form kosong lagi untuk data
        berikutnya (pola form web), dan tabel digulir ke baris baru supaya
        terlihat sudah masuk."""
        self.baru()
        iid = self.id_objek(objek)
        if self.tabel.tree.exists(iid):
            self.tabel.tree.see(iid)

    def setelah_ubah(self, objek) -> None:
        """Setelah ubah berhasil dan tabel dimuat ulang. Bawaan: tidak ada
        (baris yang sama tetap terpilih)."""

    def setelah_hapus(self, objek) -> None:
        """Setelah hapus berhasil, sebelum tabel dimuat ulang. Bawaan: form
        dikosongkan untuk tambah data baru."""
        self.baru()

    # ---- alur bersama ----

    DURASI_STATUS_MS = 6000

    def tampilkan_status(self, teks: str) -> None:
        """Pesan berhasil di bawah tombol, hilang sendiri setelah beberapa detik
        (seperti notifikasi di web); teks kosong langsung menyembunyikannya."""
        if getattr(self, "_jadwal_status", None):
            self.after_cancel(self._jadwal_status)
            self._jadwal_status = None
        self.status.tampilkan(f"✓  {teks}" if teks else "")
        if teks:
            self._jadwal_status = self.after(self.DURASI_STATUS_MS,
                                             lambda: self.tampilkan_status(""))

    def muat_ulang(self) -> None:
        """Muat ulang dropdown dan tabel; pertahankan baris terpilih jika masih ada."""
        self.muat_dropdown()
        self.muat_tabel()

    def muat_tabel(self) -> None:
        daftar = self.data()
        self.tabel.isi((o, self.nilai_baris(o), self.tag_baris(o)) for o in daftar)
        if self.dipilih is not None:
            id_dipilih = self.id_objek(self.dipilih)
            terbaru = next((o for o in daftar if self.id_objek(o) == id_dipilih), None)
            if terbaru is not None:
                # Pakai objek terbaru dari database (mis. periode yang baru ditutup).
                self.dipilih = terbaru
                self.tabel.pilih_id(id_dipilih)
            else:
                self.baru()

    def _atur_mode(self, objek) -> None:
        self.dipilih = objek
        self.judul_form.configure(text=self.teks_judul(objek))
        ubah = objek is not None
        if self.tombol_tambah is not None:
            if ubah:
                self.tombol_tambah.pack(side="left", after=self.tombol_simpan)
            else:
                self.tombol_tambah.pack_forget()
        if ubah:
            self.tombol_hapus.pack(side="right")
            self.tombol_hapus.state(["!disabled"])
        else:
            self.tombol_hapus.pack_forget()
        self.saat_mode(objek)

    def _ke_tambah(self) -> None:
        """Tinggalkan mode ubah, kembali ke form kosong untuk data baru
        (tombol "+ Tambah baru" atau Esc)."""
        if self.tombol_tambah is not None and self.dipilih is not None:
            self.baru()

    def _saat_pilih(self, objek) -> None:
        # Pilihan dilepas (objek None) tidak mengosongkan form, karena bisa
        # terjadi saat tabel dimuat ulang atau sesudah tambah.
        self._atur_mode(objek)
        if objek is not None:
            self.isi_form(objek)

    def baru(self) -> None:
        """Kosongkan form untuk menambah data baru."""
        self.tabel.lepas_pilihan()
        self._atur_mode(None)
        self.kosongkan_form()

    def _simpan(self) -> None:
        id_lama = self.id_objek(self.dipilih) if self.dipilih is not None else None
        berhasil, objek = jalankan_aman(self, lambda: self.simpan(id_lama), self.isian)
        if not berhasil:
            self.tampilkan_status("")
            return
        self.tampilkan_status(f"{kalimat(self.nama(objek))} tersimpan.")
        if id_lama is None:
            self.saat_berubah()
            self.setelah_tambah(objek)
        else:
            self.dipilih = objek
            self.saat_berubah()
            self.setelah_ubah(objek)

    def _hapus(self) -> None:
        objek = self.dipilih
        if objek is None or not konfirmasi_hapus(self, self.nama(objek)):
            return
        berhasil, _ = jalankan_aman(self, lambda: self.hapus(objek), self.isian)
        if berhasil:
            self.tampilkan_status(f"{kalimat(self.nama(objek))} dihapus.")
            self.setelah_hapus(objek)
            self.saat_berubah()
