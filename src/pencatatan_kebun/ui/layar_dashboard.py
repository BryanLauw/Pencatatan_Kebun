"""Layar Dashboard: ringkasan panen satu periode, satu tab per jenis tanaman."""
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import ClassVar

from pencatatan_kebun.services.laporan import LaporanService
from pencatatan_kebun.services.periode import PeriodeService
from pencatatan_kebun.ui.diagram import DiagramPie, warna_kategori
from pencatatan_kebun.ui.format import format_kg, format_persen, tanggal_ke_tampil
from pencatatan_kebun.ui.komponen import ComboObjek, jalankan_aman, pas_kolom
from pencatatan_kebun.ui.layar_stok import id_periode, label_periode


def _rata(total: float, jumlah: int) -> str:
    return format_kg(total / jumlah) if jumlah else "-"


class Kartu(ttk.Frame):
    """Kotak putih berisi satu angka ringkasan, mis. "Panen 120"."""

    def __init__(self, parent: tk.Widget, judul: str, angka: str, satuan: str = ""):
        super().__init__(parent, style="Kartu.TFrame", padding=(14, 6))
        ttk.Label(self, text=judul, style="Kartu.TLabel").pack(anchor="w")
        baris = ttk.Frame(self, style="Kartu.TFrame", borderwidth=0)
        baris.pack(anchor="w")
        ttk.Label(baris, text=angka, style="KartuAngka.TLabel").pack(side="left")
        if satuan:
            ttk.Label(baris, text=f" {satuan}", style="Kartu.TLabel").pack(side="left", anchor="s",
                                                                          pady=(0, 4))


class HalamanJenis(ttk.Frame):
    """Isi satu tab jenis: kartu ringkasan, dua pie, dan tabel varietas.

    Pie kanan menampilkan keterangan seluruh jenis; saat satu varietas dipilih
    di tabel, pie itu berganti ke keterangan varietas tersebut.

    Args:
        parent: Notebook jenis.
        nama_jenis: Nama jenis, mis. "Durian".
        data: Satu isian dashboard()["per_jenis"][nama_jenis].
    """

    KOLOM: ClassVar[dict[str, int]] = {"#0": 200, "stok": 70, "panen": 70, "persen": 80, "sisa": 70,
             "total": 100, "rata": 110, "minmaks": 130}
    JUDUL: ClassVar[dict[str, str]] = {"#0": "Varietas / keterangan", "stok": "Stok", "panen": "Panen", "persen": "Persen",
             "sisa": "Sisa", "total": "Total kg", "rata": "Rata-rata kg", "minmaks": "Min - maks kg"}

    def __init__(self, parent: tk.Widget, nama_jenis: str, data: dict):
        super().__init__(parent, padding=10)
        self.nama_jenis = nama_jenis
        self.ringkasan = data["ringkasan"]
        self.per_varietas = data["per_varietas"]
        self.warna_varietas = warna_kategori(list(self.per_varietas))
        self.warna_keterangan = warna_kategori(list(self.ringkasan["per_keterangan"]))

        self._buat_kartu()
        self._buat_pie()
        self._buat_tabel()
        self._tampilkan_keterangan(None)

    def _buat_kartu(self):
        r = self.ringkasan
        baris = ttk.Frame(self)
        baris.pack(fill="x")
        for judul, angka, satuan in (
                ("Stok", str(r["jumlah_stok"]), "buah"),
                ("Panen", str(r["jumlah_panen"]), "buah"),
                ("Sisa", str(r["sisa"]), "buah"),
                ("Total bobot", format_kg(r["total_bobot"]), "kg"),
                ("Rata-rata", _rata(r["total_bobot"], r["jumlah_panen"]), "kg/buah")):
            Kartu(baris, judul, angka, satuan).pack(side="left", padx=(0, 8), fill="y")

    def _buat_pie(self):
        baris = ttk.Frame(self)
        baris.pack(fill="x", pady=(8, 0))

        kiri = ttk.Frame(baris, style="Kartu.TFrame", padding=10)
        kiri.pack(side="left", padx=(0, 8))
        ttk.Label(kiri, text="Panen per varietas", style="KartuJudul.TLabel").pack(anchor="w")
        pie = DiagramPie(kiri)
        pie.pack()
        pie.tampilkan([(n, v["jumlah_panen"]) for n, v in self.per_varietas.items()],
                      self.warna_varietas)

        kanan = ttk.Frame(baris, style="Kartu.TFrame", padding=10)
        kanan.pack(side="left")
        kepala = ttk.Frame(kanan, style="Kartu.TFrame", borderwidth=0)
        kepala.pack(fill="x")
        self.judul_keterangan = ttk.Label(kepala, style="KartuJudul.TLabel")
        self.judul_keterangan.pack(side="left")
        self.tombol_seluruh = ttk.Button(kepala, text="Seluruh jenis",
                                         command=lambda: self.tree.selection_set(()))
        self.tombol_seluruh.pack(side="right")
        self.pie_keterangan = DiagramPie(kanan)
        self.pie_keterangan.pack()

    def _buat_tabel(self):
        ttk.Label(self, foreground="#52514e", text=(
            "Klik tanda di kiri nama untuk rincian keterangan. Persen: bagian dari panen jenis "
            "(baris varietas) atau dari panen varietasnya (baris keterangan).")
        ).pack(anchor="w", pady=(8, 2))
        kotak = ttk.Frame(self)
        kotak.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(kotak, columns=[k for k in self.KOLOM if k != "#0"],
                                 selectmode="browse")
        for nama, judul in self.JUDUL.items():
            self.tree.heading(nama, text=judul, anchor="w")
        pas_kolom(self.tree, self.KOLOM)
        gulir = ttk.Scrollbar(kotak, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=gulir.set)
        gulir.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        huruf_tebal = tkfont.nametofont("TkDefaultFont").copy()
        huruf_tebal.configure(weight="bold")
        self.tree.tag_configure("total", font=huruf_tebal, background="#efeee9")
        self.tree.tag_configure("keterangan", foreground="#52514e")

        r = self.ringkasan
        for nama, v in self.per_varietas.items():
            iid = f"v:{nama}"
            self.tree.insert("", "end", iid=iid, text=nama, values=(
                v["jumlah_stok"], v["jumlah_panen"],
                format_persen(v["jumlah_panen"] / r["jumlah_panen"] * 100) if r["jumlah_panen"] else "-",
                v["sisa"], format_kg(v["total_bobot"]), _rata(v["total_bobot"], v["jumlah_panen"]),
                f"{format_kg(v['bobot_min'])} - {format_kg(v['bobot_max'])}"
                if v["bobot_min"] is not None else "-"))
            self._isi_keterangan(iid, v["per_keterangan"])
        self.tree.insert("", "end", iid="total", text=f"Total {self.nama_jenis}", tags=("total",),
                         values=(r["jumlah_stok"], r["jumlah_panen"], "", r["sisa"],
                                 format_kg(r["total_bobot"]),
                                 _rata(r["total_bobot"], r["jumlah_panen"]), ""))
        self._isi_keterangan("total", r["per_keterangan"])

        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._saat_pilih())

    def _isi_keterangan(self, induk: str, per_keterangan: dict):
        """Baris anak per keterangan, tertutup sampai pengguna membukanya."""
        for nama, k in per_keterangan.items():
            self.tree.insert(induk, "end", iid=f"{induk}|{nama}", text=nama, tags=("keterangan",),
                             values=("", k["jumlah_buah"], format_persen(k["persentase"]), "",
                                     format_kg(k["total_bobot"]),
                                     _rata(k["total_bobot"], k["jumlah_buah"]), ""))

    def _saat_pilih(self):
        pilihan = self.tree.selection()
        # Baris keterangan ikut varietas induknya.
        iid = pilihan[0].split("|")[0] if pilihan else ""
        self._tampilkan_keterangan(iid[2:] if iid.startswith("v:") else None)

    def _tampilkan_keterangan(self, nama_varietas: str | None):
        if nama_varietas is None:
            data = self.ringkasan["per_keterangan"]
            self.judul_keterangan.configure(text=f"Keterangan - seluruh {self.nama_jenis}")
            self.tombol_seluruh.state(["disabled"])
        else:
            data = self.per_varietas[nama_varietas]["per_keterangan"]
            self.judul_keterangan.configure(text=f"Keterangan - {nama_varietas}")
            self.tombol_seluruh.state(["!disabled"])
        self.pie_keterangan.tampilkan([(n, k["jumlah_buah"]) for n, k in data.items()],
                                      self.warna_keterangan)


class LayarDashboard(ttk.Frame):
    """Tab Dashboard (layar pembuka).

    Args:
        parent: Notebook jendela utama.
        service: LaporanService.
        periode_service: PeriodeService, untuk daftar periode.
    """

    def __init__(self, parent: tk.Widget, service: LaporanService, periode_service: PeriodeService):
        super().__init__(parent, padding=10)
        self.service = service
        self.periode_service = periode_service

        atas = ttk.Frame(self)
        atas.pack(fill="x")
        ttk.Label(atas, text="Periode").pack(side="left", padx=(0, 6))
        self.combo_periode = ComboObjek(atas, label_periode, id_periode, width=22)
        self.combo_periode.pack(side="left")
        self.combo_periode.bind("<<ComboboxSelected>>", lambda _e: self._muat_isi())
        self.rentang = ttk.Label(atas, foreground="#52514e")
        self.rentang.pack(side="left", padx=12)

        self.isi = ttk.Frame(self)
        self.isi.pack(fill="both", expand=True, pady=(8, 0))
        self.muat_ulang()

    def muat_ulang(self) -> None:
        """Muat ulang daftar periode dan isi dashboard (periode terpilih dipertahankan)."""
        daftar = self.periode_service.daftar_periode()
        self.combo_periode.isi(daftar)
        if self.combo_periode.terpilih() is None:
            aktif = self.periode_service.periode_aktif()
            if aktif is not None:
                self.combo_periode.pilih_id(aktif.get_id_periode())
            elif daftar:
                self.combo_periode.pilih_id(daftar[-1].get_id_periode())
        self._muat_isi()

    def _muat_isi(self) -> None:
        tab_lama = None
        for anak in self.isi.winfo_children():
            if isinstance(anak, ttk.Notebook) and anak.select():
                tab_lama = anak.tab(anak.select(), "text")
            anak.destroy()

        periode = self.combo_periode.terpilih()
        if periode is None:
            self.rentang.configure(text="")
            self._pesan("Belum ada periode panen. Buka periode di tab Periode Panen.")
            return
        selesai = periode.get_tanggal_selesai()
        self.rentang.configure(text=f"{tanggal_ke_tampil(periode.get_tanggal_mulai())} s.d. "
                                    f"{tanggal_ke_tampil(selesai) if selesai else 'sekarang'}")
        berhasil, data = jalankan_aman(self, lambda: self.service.dashboard(periode.get_id_periode()))
        if not berhasil:
            return
        if not data["per_jenis"]:
            self._pesan("Belum ada stok atau panen di periode ini. Isi stok di tab Stok Pohon "
                        "dan catat buah di tab Catat Panen.")
            return

        tab = ttk.Notebook(self.isi)
        tab.pack(fill="both", expand=True)
        for nama, data_jenis in data["per_jenis"].items():
            halaman = HalamanJenis(tab, nama, data_jenis)
            tab.add(halaman, text=nama)
            if nama == tab_lama:
                tab.select(halaman)

    def _pesan(self, teks: str) -> None:
        ttk.Label(self.isi, text=teks, style="Judul.TLabel", foreground="#52514e").pack(
            anchor="w", pady=20)
