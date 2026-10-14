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
    # clam dipakai karena warna latar isian bisa diubah (untuk menyorot isian salah).
    gaya.theme_use("clam")

    for nama in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(nama).configure(size=UKURAN_HURUF)
    huruf = tkfont.nametofont("TkDefaultFont")
    root.option_add("*TCombobox*Listbox.font", huruf)

    gaya.configure("Treeview", rowheight=huruf.metrics("linespace") + 10)
    gaya.configure("Treeview.Heading", font=(huruf.actual("family"), UKURAN_HURUF, "bold"))
    gaya.configure("TButton", padding=(12, 6))
    gaya.configure("TNotebook.Tab", padding=(16, 6))
    gaya.configure("Judul.TLabel", font=(huruf.actual("family"), UKURAN_HURUF + 2, "bold"))

    # Kartu putih di Dashboard (ringkasan angka dan pie).
    keluarga = huruf.actual("family")
    gaya.configure("Kartu.TFrame", background="#ffffff", relief="solid", borderwidth=1)
    gaya.configure("Kartu.TLabel", background="#ffffff", foreground="#52514e")
    gaya.configure("KartuJudul.TLabel", background="#ffffff", foreground="#0b0b0b",
                   font=(keluarga, UKURAN_HURUF, "bold"))
    gaya.configure("KartuAngka.TLabel", background="#ffffff", foreground="#0b0b0b",
                   font=(keluarga, UKURAN_HURUF + 6, "bold"))

    gaya.configure("Salah.TEntry", fieldbackground=WARNA_SALAH)
    gaya.map("Salah.TCombobox", fieldbackground=[("readonly", WARNA_SALAH)])


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

    def sesuaikan(event) -> None:
        for nama, lebar in kolom.items():
            tree.column(nama, width=max(20, event.width * lebar // total))

    tree.bind("<Configure>", sesuaikan, add="+")


class Tabel(ttk.Frame):
    """Tabel (Treeview) dengan scrollbar yang tiap barisnya mewakili satu objek.

    Args:
        parent: Widget induk.
        kolom: Daftar (judul, lebar) tiap kolom.
        id_fn: Fungsi objek -> id, dipakai sebagai id baris.
        saat_pilih: Dipanggil dengan objek baris yang dipilih (atau None).
    """

    def __init__(self, parent: tk.Widget, kolom: Sequence[tuple[str, int]],
                 id_fn: Callable[[object], str],
                 saat_pilih: Callable[[object | None], None] | None = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.id_fn = id_fn
        self.saat_pilih = saat_pilih
        self._objek: dict[str, object] = {}

        nama_kolom = [f"k{i}" for i in range(len(kolom))]
        self.tree = ttk.Treeview(self, columns=nama_kolom, show="headings", selectmode="browse")
        for nama, (judul, _) in zip(nama_kolom, kolom):
            self.tree.heading(nama, text=judul, anchor="w")
            self.tree.column(nama, anchor="w")
        pas_kolom(self.tree, {nama: lebar for nama, (_, lebar) in zip(nama_kolom, kolom)})
        gulir = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=gulir.set)
        # Scrollbar dipasang dulu supaya tidak terdesak keluar saat ruang sempit.
        gulir.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._saat_pilih)

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
    """Letakkan label dan isian di satu baris form (grid dua kolom).

    Returns:
        widget, supaya bisa langsung disimpan ke atribut.
    """
    ttk.Label(frame, text=label).grid(row=baris, column=0, sticky="w", pady=4, padx=(0, 8))
    widget.grid(row=baris, column=1, sticky="w", pady=4)
    return widget


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


class PanelCrud(ttk.Frame):
    """Pola layar daftar + form: tabel di kiri, form di kanan.

    Klik baris tabel -> form terisi (mode ubah). Tombol "Baru" -> form kosong
    (mode tambah). "Simpan" (atau Enter di isian) memanggil simpan(id) dengan
    id None saat menambah. Turunan mengisi atribut kelas dan menimpa fungsi di
    bagian "timpa di turunan".

    Args:
        parent: Widget induk.
        service: Service yang dipakai turunan.
        saat_berubah: Dipanggil setelah data tersimpan atau terhapus, agar
            layar lain memuat ulang datanya.
    """

    nama_data = "data"          # untuk judul form, mis. "jenis"
    kolom: tuple[tuple[str, int], ...] = ()
    pakai_tombol_baru = True    # False jika data hanya bisa dipilih dari tabel

    def __init__(self, parent: tk.Widget, service, saat_berubah: Callable[[], None]):
        super().__init__(parent, padding=10)
        self.service = service
        self.saat_berubah = saat_berubah
        self.dipilih: object | None = None
        # Peta nama kolom exception -> widget isian, untuk menyorot isian salah.
        self.isian: dict[str, tk.Widget] = {}

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        kotak_filter = ttk.Frame(self)
        kotak_filter.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.buat_filter(kotak_filter)

        self.tabel = Tabel(self, self.kolom, self.id_objek, saat_pilih=self._saat_pilih)
        self.tabel.grid(row=1, column=0, sticky="nsew")

        kanan = ttk.Frame(self, padding=(16, 0, 0, 0))
        kanan.grid(row=0, column=1, rowspan=2, sticky="n")
        self.judul_form = ttk.Label(kanan, style="Judul.TLabel")
        self.judul_form.pack(anchor="w", pady=(0, 8))

        form = ttk.Frame(kanan)
        form.pack(anchor="w", fill="x")
        self.buat_form(form)
        for entry in _semua_entry(form):
            entry.bind("<Return>", lambda _e: self._simpan())

        tombol = ttk.Frame(kanan)
        tombol.pack(anchor="w", pady=(12, 0))
        if self.pakai_tombol_baru:
            ttk.Button(tombol, text="Baru", command=self.baru).pack(side="left", padx=(0, 6))
        ttk.Button(tombol, text="Simpan", command=self._simpan).pack(side="left", padx=(0, 6))
        self.tombol_hapus = ttk.Button(tombol, text="Hapus", command=self._hapus)
        self.tombol_hapus.pack(side="left")
        self.buat_tombol(kanan)

        self.status = ttk.Label(kanan, foreground="#1a7f37", wraplength=skala(self, 380))
        self.status.pack(anchor="w", pady=(12, 0))

        self.muat_ulang()
        self.baru()

    # ---- timpa di turunan ----

    def buat_filter(self, frame: ttk.Frame) -> None:
        """Isian filter di atas tabel. Bawaan: tidak ada."""

    def buat_form(self, frame: ttk.Frame) -> None:
        raise NotImplementedError

    def buat_tombol(self, frame: ttk.Frame) -> None:
        """Tombol tambahan di bawah Baru/Simpan/Hapus. Bawaan: tidak ada."""

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
        """Setelah tambah berhasil. Bawaan: pilih baris baru (mode ubah), atau
        kosongkan form jika baris baru tersembunyi oleh filter."""
        if not self.tabel.pilih_id(self.id_objek(objek)):
            self.baru()

    def setelah_ubah(self, objek) -> None:
        """Setelah ubah berhasil dan tabel dimuat ulang. Bawaan: tidak ada
        (baris yang sama tetap terpilih)."""

    def setelah_hapus(self, objek) -> None:
        """Setelah hapus berhasil, sebelum tabel dimuat ulang. Bawaan: form
        dikosongkan untuk tambah data baru."""
        self.baru()

    # ---- alur bersama ----

    def tampilkan_status(self, teks: str) -> None:
        """Pesan berhasil di bawah tombol."""
        self.status.configure(text=teks)

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
        self.tombol_hapus.state(["disabled"] if objek is None else ["!disabled"])
        self.saat_mode(objek)

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
