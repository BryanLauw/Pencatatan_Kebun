"""Pie chart sederhana di tk.Canvas (tanpa matplotlib)."""
import tkinter as tk
from tkinter import font as tkfont

from pencatatan_kebun.ui.format import format_persen
from pencatatan_kebun.ui.komponen import skala

# Palet kategori (urutan tetap, tidak diulang): biru, oranye, aqua, kuning,
# magenta, hijau, ungu, merah. "Lainnya" selalu abu-abu.
PALET = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
WARNA_LAINNYA = "#9e9d98"
WARNA_LATAR = "#ffffff"
WARNA_TEKS = "#0b0b0b"
WARNA_TEKS_REDUP = "#52514e"
MAKS_IRISAN = 6
LABEL_LAINNYA = "Lainnya"


# ---- logika (tanpa tkinter, diuji di tests/test_ui_diagram.py) ----

def warna_kategori(nama: list[str]) -> dict[str, str]:
    """Warna tiap kategori menurut urutannya, mis. urutan nama keterangan.

    Warna mengikuti kategori, bukan besar nilainya, jadi "Baik" tetap biru
    di pie jenis maupun pie varietas. Kategori setelah slot ke-8 abu-abu.
    """
    return {n: PALET[i] if i < len(PALET) else WARNA_LAINNYA for i, n in enumerate(nama)}


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
        self.huruf_kecil.configure(size=max(9, self.huruf.cget("size") - 2))

    def tampilkan(self, data: list[tuple[str, float]], warna: dict[str, str],
                  satuan: str = "buah") -> None:
        """Gambar ulang pie.

        Args:
            data: Daftar (label, nilai). Nilai 0 tidak digambar; lebih dari
                MAKS_IRISAN irisan digabung menjadi "Lainnya".
            warna: Warna per label (lihat warna_kategori).
            satuan: Satuan nilai di legenda, mis. "buah".
        """
        self.delete("all")
        data = kelompokkan(data)
        total = sum(nilai for _, nilai in data)
        lebar, tinggi = int(self.cget("width")), int(self.cget("height"))
        if total <= 0:
            self.create_text(lebar // 2, tinggi // 2, text="Belum ada panen",
                             fill=WARNA_TEKS_REDUP, font=self.huruf)
            return

        jarak = skala(self, 10)
        r = min(tinggi // 2 - jarak, lebar // 4)
        cx, cy = jarak + r, tinggi // 2
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
        x = cx + r + skala(self, 24)
        baris_nama = self.huruf.metrics("linespace")
        baris_angka = self.huruf_kecil.metrics("linespace")
        tinggi_entri = baris_nama + baris_angka + skala(self, 4)
        y = cy - tinggi_entri * len(data) / 2
        sisi = skala(self, 12)
        for label, nilai in data:
            tengah = y + baris_nama / 2
            self.create_rectangle(x, tengah - sisi / 2, x + sisi, tengah + sisi / 2,
                                  fill=warna.get(label, WARNA_LAINNYA), outline="")
            kiri = x + sisi + skala(self, 8)
            self.create_text(kiri, tengah, anchor="w", text=label, fill=WARNA_TEKS,
                             font=self.huruf)
            angka = f"{nilai:g} {satuan} · {format_persen(nilai / total * 100)}"
            self.create_text(kiri, y + baris_nama, anchor="nw", text=angka,
                             fill=WARNA_TEKS_REDUP, font=self.huruf_kecil)
            y += tinggi_entri
