"""Pie chart sederhana di tk.Canvas (tanpa matplotlib)."""
import tkinter as tk
from tkinter import font as tkfont

from pencatatan_kebun.ui.format import format_persen
from pencatatan_kebun.ui.komponen import skala

# Palet kategori umum (mis. varietas), urutan tetap dan tidak diulang: biru, ungu,
# toska, merah muda, cokelat, abu kebiruan, nila, lembayung. Sengaja tanpa hijau,
# kuning, dan merah, karena tiga warna itu sudah bermakna di keterangan buah.
# "Lainnya" selalu abu-abu.
PALET = ["#3b82c4", "#7a6bd0", "#2a9d8f", "#c76b98", "#a0703c", "#5b7083", "#4652b8", "#9a5fa8"]

# Warna bermakna untuk keterangan buah: baik = hijau, gugur = kuning tua, rusak = merah.
# Dicocokkan dengan nama keterangan (huruf besar/kecil diabaikan); nama lain memakai PALET.
WARNA_BAIK = "#2f7d4f"
WARNA_GUGUR = "#e0a020"
WARNA_RUSAK = "#d9534f"
WARNA_MAKNA = {
    "baik": WARNA_BAIK, "bagus": WARNA_BAIK, "layak": WARNA_BAIK,
    "gugur": WARNA_GUGUR, "jatuh": WARNA_GUGUR,
    "rusak": WARNA_RUSAK, "busuk": WARNA_RUSAK, "cacat": WARNA_RUSAK,
}
WARNA_LAINNYA = "#9e9d98"
WARNA_LATAR = "#ffffff"
WARNA_TEKS = "#0b0b0b"
WARNA_TEKS_REDUP = "#52514e"
MAKS_IRISAN = 6
LABEL_LAINNYA = "Lainnya"


# ---- logika (tanpa tkinter, diuji di tests/test_ui_diagram.py) ----

def warna_kategori(nama: list[str]) -> dict[str, str]:
    """Warna tiap kategori menurut urutannya, mis. urutan nama keterangan.

    Warna mengikuti kategori, bukan besar nilainya, jadi satu varietas tetap
    berwarna sama di semua pie. Kategori setelah slot ke-8 abu-abu.
    """
    return {n: PALET[i] if i < len(PALET) else WARNA_LAINNYA for i, n in enumerate(nama)}


def warna_keterangan(nama: list[str]) -> dict[str, str]:
    """Warna tiap keterangan buah: nama yang bermakna (lihat WARNA_MAKNA) memakai
    warnanya, mis. "Baik" hijau dan "Rusak" merah; nama lain memakai PALET
    menurut urutannya, lalu abu-abu jika PALET habis.
    """
    sisa = iter(PALET)
    return {n: WARNA_MAKNA.get(n.strip().lower()) or next(sisa, WARNA_LAINNYA) for n in nama}


def kelompokkan(data: list[tuple[str, float]], maks: int = MAKS_IRISAN) -> list[tuple[str, float]]:
    """Buang nilai 0, lalu gabungkan yang terkecil menjadi "Lainnya" jika
    irisannya lebih dari maks.

    Args:
        data: Daftar (label, nilai), urutan dipertahankan.
        maks: Jumlah irisan paling banyak, termasuk "Lainnya".

    Returns:
        Daftar (label, nilai) dengan urutan asli; "Lainnya" (jika ada) di akhir.
    """
    data = [(label, nilai) for label, nilai in data if nilai > 0]
    if len(data) <= maks:
        return data
    besar = sorted(data, key=lambda d: d[1], reverse=True)[:maks - 1]
    simpan = {label for label, _ in besar}
    hasil = [d for d in data if d[0] in simpan]
    hasil.append((LABEL_LAINNYA, sum(nilai for label, nilai in data if label not in simpan)))
    return hasil


# ---- widget ----

class DiagramPie(tk.Canvas):
    """Pie chart dengan legenda di sebelah kanan: nama, lalu jumlah dan persen
    di baris bawahnya (supaya nama panjang tidak menabrak angka).

    Args:
        parent: Widget induk.
        lebar: Lebar kanvas dalam piksel layar 100% (ikut skala tampilan).
        tinggi: Tinggi kanvas dalam piksel layar 100%.
    """

    def __init__(self, parent: tk.Widget, lebar: int = 400, tinggi: int = 170, **kwargs):
        super().__init__(parent, width=skala(parent, lebar), height=skala(parent, tinggi),
                         background=WARNA_LATAR, highlightthickness=0, **kwargs)
        self.huruf = tkfont.nametofont("TkDefaultFont")
        self.huruf_kecil = self.huruf.copy()
        # Satu poin di bawah huruf biasa (11 pt ≈ 15 px): masih jelas lebih kecil
        # dari nama, tetapi tidak di bawah 14 px, batas teks sekunder yang nyaman.
        self.huruf_kecil.configure(size=max(11, self.huruf.cget("size") - 1))
        self._terakhir: tuple | None = None
        # Gambar ulang saat kanvas melebar atau menyempit mengikuti kartunya.
        self.bind("<Configure>", self._saat_ukuran_berubah)

    def _saat_ukuran_berubah(self, _event) -> None:
        if self._terakhir is not None:
            self.tampilkan(*self._terakhir)

    def tampilkan(self, data: list[tuple[str, float]], warna: dict[str, str],
                  satuan: str = "buah") -> None:
        """Gambar ulang pie.

        Args:
            data: Daftar (label, nilai). Nilai 0 tidak digambar; lebih dari
                MAKS_IRISAN irisan digabung menjadi "Lainnya".
            warna: Warna per label (lihat warna_kategori).
            satuan: Satuan nilai di legenda, mis. "buah".
        """
        self._terakhir = (data, warna, satuan)
        self.delete("all")
        data = kelompokkan(data)
        total = sum(nilai for _, nilai in data)
        # Ukuran sebenarnya (bisa lebih besar dari yang diminta); sebelum
        # tampil winfo_* bernilai 1, jadi pakai ukuran yang diminta.
        lebar = max(self.winfo_width(), int(self.cget("width")))
        tinggi = max(self.winfo_height(), int(self.cget("height")))
        if total <= 0:
            self.create_text(lebar // 2, tinggi // 2, text="Belum ada panen",
                             fill=WARNA_TEKS_REDUP, font=self.huruf)
            return

        jarak = skala(self, 10)
        r = min(tinggi // 2 - jarak, lebar // 4)
        sisi = skala(self, 12)
        celah_legenda = skala(self, 24)
        teks_angka = {label: f"{nilai:g} {satuan} · {format_persen(nilai / total * 100)}"
                      for label, nilai in data}
        lebar_legenda = sisi + skala(self, 8) + max(
            max(self.huruf.measure(label), self.huruf_kecil.measure(teks_angka[label]))
            for label, _ in data)
        # Pie dan legenda sebagai satu kelompok di tengah kanvas, supaya kartu
        # yang lebar tidak menyisakan ruang kosong di satu sisi saja.
        kiri_kelompok = max(jarak, (lebar - (2 * r + celah_legenda + lebar_legenda)) // 2)
        cx, cy = kiri_kelompok + r, tinggi // 2
        kotak = (cx - r, cy - r, cx + r, cy + r)
        if len(data) == 1:
            label = data[0][0]
            self.create_oval(*kotak, fill=warna.get(label, WARNA_LAINNYA), outline=WARNA_LATAR)
        else:
            # Mulai dari atas, searah jarum jam; garis 2px warna latar = celah antar irisan.
            mulai = 90.0
            for label, nilai in data:
                sudut = nilai / total * 360
                self.create_arc(*kotak, start=mulai, extent=-sudut, style="pieslice",
                                fill=warna.get(label, WARNA_LAINNYA), outline=WARNA_LATAR,
                                width=2)
                mulai -= sudut

        # Legenda: identitas tidak hanya dari warna, angkanya memakai warna teks biasa.
        x = cx + r + celah_legenda
        baris_nama = self.huruf.metrics("linespace")
        baris_angka = self.huruf_kecil.metrics("linespace")
        tinggi_entri = baris_nama + baris_angka + skala(self, 4)
        y = cy - tinggi_entri * len(data) / 2
        for label, _nilai in data:
            tengah = y + baris_nama / 2
            self.create_rectangle(x, tengah - sisi / 2, x + sisi, tengah + sisi / 2,
                                  fill=warna.get(label, WARNA_LAINNYA), outline="")
            kiri = x + sisi + skala(self, 8)
            self.create_text(kiri, tengah, anchor="w", text=label, fill=WARNA_TEKS,
                             font=self.huruf)
            self.create_text(kiri, y + baris_nama, anchor="nw", text=teks_angka[label],
                             fill=WARNA_TEKS_REDUP, font=self.huruf_kecil)
            y += tinggi_entri
