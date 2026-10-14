"""Layar Catat Panen: catat satu buah per simpan, dan daftar buah per tanggal."""
import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from pencatatan_kebun.models import Buah, KeteranganBuah, Pohon
from pencatatan_kebun.services.exception import (
    BobotTidakValidException,
    DataTidakDitemukanException,
)
from pencatatan_kebun.services.master import MasterService
from pencatatan_kebun.services.panen import PanenService
from pencatatan_kebun.services.periode import PeriodeService
from pencatatan_kebun.services.stok import StokService
from pencatatan_kebun.ui.format import format_kg, tanggal_ke_tampil, teks_ke_bobot
from pencatatan_kebun.ui.kalender import EntryTanggal
from pencatatan_kebun.ui.komponen import (
    ComboObjek,
    Dibatalkan,
    PanelCrud,
    baris_isian,
    set_entry,
    skala,
    wajib_pilih,
)
from pencatatan_kebun.ui.layar_master import (
    id_jenis,
    id_varietas,
    label_jenis,
    label_varietas,
)


def _nama_pohon(pohon: Pohon) -> str:
    return f"{label_varietas(pohon.get_varietas())} nomor {pohon.get_nomor_pohon()}"


class LayarPanen(PanelCrud):
    """Tab Catat Panen.

    Tanggal panen dipilih di atas dan dipakai untuk dua hal: daftar buah di
    tabel dan tanggal buah yang dicatat. Satu buah per simpan: setelah simpan
    hanya bobot yang dikosongkan, pilihan pohon dan keterangan tetap.

    Sebelum mencatat, aplikasi memperingatkan (tidak memblokir) jika sisa buah
    pohon di periode itu sudah habis, pohon belum punya stok, atau tanggalnya
    di luar semua periode.

    Args:
        parent: Widget induk (Notebook jendela utama).
        service: PanenService.
        master_service: MasterService, untuk dropdown jenis/varietas/pohon/keterangan.
        periode_service: PeriodeService, untuk periode pada tanggal panen.
        stok_service: StokService, untuk sisa buah pohon.
        saat_berubah: Dipanggil setelah catatan buah berubah, agar layar Stok
            dan Dashboard memuat ulang.
    """

    nama_data = "buah"
    kolom = (("No.", 45), ("Jenis", 110), ("Varietas", 150), ("Pohon", 70),
             ("Keterangan", 120), ("Bobot (kg)", 100))

    def __init__(self, parent: tk.Widget, service: PanenService, master_service: MasterService,
                 periode_service: PeriodeService, stok_service: StokService,
                 saat_berubah: Callable[[], None]):
        self.master_service = master_service
        self.periode_service = periode_service
        self.stok_service = stok_service
        self._saat_panen_berubah = saat_berubah
        super().__init__(parent, service, self._berubah)

        self.total = ttk.Label(self, foreground="#333")
        self.total.grid(row=2, column=0, sticky="w", pady=(6, 0))
        self._perbarui_total()

    def _berubah(self):
        self.muat_ulang()
        self._saat_panen_berubah()

    # ---- tanggal dan tabel ----

    def buat_filter(self, frame):
        ttk.Label(frame, text="Tanggal panen").pack(side="left", padx=(0, 8))
        self.tgl = EntryTanggal(frame, "tanggal_panen", "Tanggal panen", sampai_hari_ini=True)
        self.tgl.pack(side="left")
        # Dipasang setelah tanggal terisi, karena tabel belum ada saat ini.
        self.tgl.saat_berubah = lambda _t: self._ganti_tanggal()

    def _ganti_tanggal(self):
        self.muat_tabel()
        self._perbarui_info()

    def data(self):
        return self.service.daftar_buah_per_tanggal(self.tgl.get_db())

    def muat_tabel(self):
        super().muat_tabel()
        # Nomor urut baris diisi setelah tabel terisi.
        for urutan, iid in enumerate(self.tabel.tree.get_children(), start=1):
            self.tabel.tree.set(iid, "k0", urutan)
        if hasattr(self, "total"):
            self._perbarui_total()

    def _perbarui_total(self):
        daftar = self.tabel.semua()
        tanggal = tanggal_ke_tampil(self.tgl.get_db())
        if not daftar:
            self.total.configure(text=f"Belum ada buah tercatat pada {tanggal}.")
            return
        bobot = sum(b.get_bobot() for b in daftar)
        self.total.configure(text=f"{len(daftar)} buah pada {tanggal}, total {format_kg(bobot)} kg")

    def id_objek(self, objek):
        return objek.get_id_buah()

    def nilai_baris(self, objek):
        pohon = objek.get_pohon()
        varietas = pohon.get_varietas()
        return ("", varietas.get_jenis().get_nama_jenis(), varietas.get_nama_varietas(),
                pohon.get_nomor_pohon(), objek.get_keterangan().get_nama_keterangan(),
                format_kg(objek.get_bobot()))

    # ---- dropdown ----

    def muat_dropdown(self):
        self.combo_jenis.isi(self.master_service.daftar_jenis())
        if self.combo_jenis.terpilih() is None:
            self._pilih_jika_satu(self.combo_jenis)
        self._isi_varietas()
        self.combo_keterangan.isi(self.master_service.daftar_keterangan())
        if self.combo_keterangan.terpilih() is None:
            self._pilih_jika_satu(self.combo_keterangan)

    @staticmethod
    def _pilih_jika_satu(combo: ComboObjek):
        if len(combo.cget("values")) == 1:
            combo.current(0)

    def _isi_varietas(self):
        jenis = self.combo_jenis.terpilih()
        self.combo_varietas.isi(self.master_service.daftar_varietas(jenis) if jenis else [])
        if self.combo_varietas.terpilih() is None:
            self._pilih_jika_satu(self.combo_varietas)
        self._isi_pohon()

    def _isi_pohon(self):
        varietas = self.combo_varietas.terpilih()
        self.combo_pohon.isi(self.master_service.daftar_pohon(varietas) if varietas else [])
        self._perbarui_info()

    # ---- form ----

    def buat_form(self, frame):
        self.combo_jenis = baris_isian(frame, 0, "Jenis", ComboObjek(
            frame, label_jenis, id_jenis, width=22))
        self.combo_varietas = baris_isian(frame, 1, "Varietas", ComboObjek(
            frame, lambda v: v.get_nama_varietas(), id_varietas, width=22))
        self.combo_pohon = baris_isian(frame, 2, "Pohon", ComboObjek(
            frame, lambda p: f"Nomor {p.get_nomor_pohon()}", lambda p: p.get_id_pohon(), width=22))
        self.combo_keterangan = baris_isian(frame, 3, "Keterangan", ComboObjek(
            frame, lambda k: k.get_nama_keterangan(), lambda k: k.get_id_keterangan(), width=22))
        self.entry_bobot = baris_isian(frame, 4, "Bobot (kg)", ttk.Entry(frame, width=10))
        self.combo_jenis.bind("<<ComboboxSelected>>", lambda _e: self._isi_varietas())
        self.combo_varietas.bind("<<ComboboxSelected>>", lambda _e: self._isi_pohon())
        self.combo_pohon.bind("<<ComboboxSelected>>", lambda _e: self._pohon_dipilih())

        self.info = ttk.Label(frame, foreground="#555", wraplength=skala(frame, 340))
        self.info.grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(frame, text="Tekan Enter untuk simpan. Pohon dan keterangan tidak "
                              "dikosongkan, jadi buah berikutnya cukup diisi bobotnya.",
                  foreground="#555", wraplength=skala(frame, 340)).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.isian = {"pohon": self.combo_pohon, "keterangan_buah": self.combo_keterangan,
                      "bobot": self.entry_bobot, "tanggal_panen": self.tgl.entry}

    def _pohon_dipilih(self):
        self._perbarui_info()
        self.entry_bobot.focus_set()

    def teks_judul(self, objek):
        return "Catat buah" if objek is None else "Ubah catatan buah"

    def isi_form(self, objek: Buah):
        pohon = objek.get_pohon()
        varietas = pohon.get_varietas()
        self.combo_jenis.pilih_id(varietas.get_jenis().get_id_jenis())
        self._isi_varietas()
        self.combo_varietas.pilih_id(varietas.get_id_varietas())
        self._isi_pohon()
        self.combo_pohon.pilih_id(pohon.get_id_pohon())
        self.combo_keterangan.pilih_id(objek.get_keterangan().get_id_keterangan())
        set_entry(self.entry_bobot, f"{objek.get_bobot():g}".replace(".", ","))
        self._perbarui_info()

    def kosongkan_form(self):
        # Hanya bobot: pohon dan keterangan dipakai lagi untuk buah berikutnya.
        set_entry(self.entry_bobot, "")
        self.entry_bobot.focus_set()
        self._perbarui_info()

    def setelah_tambah(self, objek):
        self.baru()

    # ---- sisa buah dan peringatan #8 ----

    def _cek_sisa(self, pohon: Pohon, tanggal: str) -> tuple[str, str | None]:
        """Info sisa buah pohon di periode pada tanggal panen.

        Returns:
            (teks info di bawah form, pesan peringatan atau None jika aman).
        """
        tampil = tanggal_ke_tampil(tanggal)
        periode = self.periode_service.periode_pada_tanggal(tanggal)
        if periode is None:
            return (f"Tanggal {tampil} di luar semua periode panen.",
                    (f"Tanggal {tampil} tidak termasuk periode panen mana pun, jadi buah ini "
                     "tidak masuk laporan periode."))
        try:
            sisa = self.stok_service.sisa_buah(pohon.get_id_pohon(), periode.get_id_periode())
        except DataTidakDitemukanException:
            return (f"Pohon ini belum punya stok di periode {periode.get_nama()}.",
                    (f"Pohon {_nama_pohon(pohon)} belum punya stok di periode "
                     f"{periode.get_nama()}, jadi sisa buahnya tidak bisa dihitung."))
        info = f"Sisa buah pohon ini di periode {periode.get_nama()}: {sisa}"
        if sisa <= 0:
            return (info, (f"Sisa buah pohon {_nama_pohon(pohon)} di periode "
                           f"{periode.get_nama()} sudah {sisa}. Buah ini membuat panen "
                           "melebihi stok pohon."))
        return info, None

    def _perbarui_info(self):
        if not hasattr(self, "info"):
            return
        pohon = self.combo_pohon.terpilih()
        self.info.configure(text=self._cek_sisa(pohon, self.tgl.get_db())[0] if pohon else "")

    def _konfirmasi_sisa(self, pohon: Pohon, tanggal: str) -> None:
        """Peringatan #8: tanya dulu jika sisa habis/tidak diketahui.

        Raises:
            Dibatalkan: Pengguna memilih Tidak.
        """
        _, peringatan = self._cek_sisa(pohon, tanggal)
        if peringatan is not None and not messagebox.askyesno(
                "Periksa sisa buah", f"{peringatan}\n\nTetap simpan?",
                icon="warning", default="no", parent=self):
            raise Dibatalkan()

    # ---- simpan dan hapus ----

    def simpan(self, id_lama):
        pohon = wajib_pilih(self.combo_pohon.terpilih(), "Pohon", "pohon")
        keterangan: KeteranganBuah = wajib_pilih(self.combo_keterangan.terpilih(),
                                                 "Keterangan", "keterangan_buah")
        bobot = teks_ke_bobot(self.entry_bobot.get())
        tanggal = self.tgl.get_db()
        # Bobot dicek dulu supaya peringatan sisa tidak muncul untuk isian yang salah.
        if bobot is None or bobot <= 0:
            raise BobotTidakValidException()
        # Saat ubah, buah ini sudah terhitung di sisa pohonnya; peringatan hanya
        # jika dipindah ke pohon lain.
        if id_lama is None or pohon.get_id_pohon() != self.dipilih.get_pohon().get_id_pohon():
            self._konfirmasi_sisa(pohon, tanggal)
        if id_lama is None:
            return self.service.catat_buah(pohon, keterangan, bobot, tanggal)
        return self.service.ubah_catatan_buah(id_lama, pohon, keterangan, bobot, tanggal)

    def hapus(self, objek):
        self.service.hapus_catatan_buah(objek.get_id_buah())

    def nama(self, objek):
        return f"buah {_nama_pohon(objek.get_pohon())} ({format_kg(objek.get_bobot())} kg)"
