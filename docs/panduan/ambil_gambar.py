"""Ambil gambar layar untuk panduan (docs/panduan/gambar/*.png).

Jalankan ulang jika tampilan aplikasi berubah, dari folder proyek:

    .venv\\Scripts\\python docs\\panduan\\ambil_gambar.py

Memakai database contoh di folder sementara (database asli tidak tersentuh).
Jendela aplikasi muncul beberapa detik. Gambar diambil dengan PrintWindow,
jadi tidak terpengaruh jendela lain yang menutupinya.
"""
import ctypes
import random
import struct
import sys
import tempfile
import time
import zlib
from ctypes import wintypes
from pathlib import Path

PROYEK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROYEK / "src"))

from pencatatan_kebun.cadangan import CadanganService
from pencatatan_kebun.db.koneksi import buka_koneksi
from pencatatan_kebun.services.laporan import LaporanService
from pencatatan_kebun.services.master import MasterService
from pencatatan_kebun.services.panen import PanenService
from pencatatan_kebun.services.periode import PeriodeService
from pencatatan_kebun.services.stok import StokService
from pencatatan_kebun.ui.jendela_utama import JendelaUtama
from pencatatan_kebun.ui.komponen import set_entry

FOLDER_GAMBAR = Path(__file__).parent / "gambar"
TANDA_PNG = bytes([0x89]) + b"PNG" + bytes([13, 10, 26, 10])


def isi_contoh(conn):
    """Data contoh: 2 jenis, beberapa varietas dan pohon, satu periode berjalan."""
    random.seed(7)
    m, per, st, pn = MasterService(conn), PeriodeService(conn), StokService(conn), PanenService(conn)
    ket = {n: m.tambah_keterangan(n, d) for n, d in (
        ("Baik", "Buah layak jual"), ("Gugur", "Jatuh sebelum dipetik"),
        ("Rusak", "Busuk, retak, atau dimakan hewan"))}
    pohon = []
    for jenis, daftar, bobot in (("Durian", (("Bawor", 4), ("Musang King", 3), ("Montong", 2)),
                                  (1.5, 3.5)),
                                 ("Alpukat", (("Mentega", 3), ("Aligator", 2)), (0.3, 0.6))):
        j = m.tambah_jenis(jenis)
        for nama, jumlah in daftar:
            v = m.tambah_varietas(j, nama)
            pohon += [(m.tambah_pohon(v, i), bobot) for i in range(1, jumlah + 1)]
    per.buka_periode("Gadu 2026", "2026-03-01", "2026-05-31", "Panen kecil")
    raya = per.buka_periode("Raya 2026", "2026-09-01", None, "Panen raya")
    tanggal = [f"2026-09-{h:02d}" for h in (8, 12, 15, 19, 22, 26, 29)] + \
              [f"2026-10-{h:02d}" for h in (2, 6, 9, 13)]
    for i, (p, (bawah, atas)) in enumerate(pohon):
        if i == len(pohon) - 1:
            continue  # satu pohon belum dihitung (abu-abu di tab Stok)
        stok = random.randint(8, 15)
        st.catat_stok(p, raya, stok, "2026-09-03")
        for _ in range(random.randint(stok // 2, stok)):
            keterangan = random.choices(list(ket.values()), weights=(75, 15, 10))[0]
            pn.catat_buah(p, keterangan, round(random.uniform(bawah, atas), 1),
                          random.choice(tanggal))
    return pohon, ket


def _tulis_png(lokasi: Path, lebar: int, tinggi: int, bgra: bytes) -> None:
    """Tulis piksel BGRA (baris dari atas) sebagai PNG RGB, tanpa library luar."""
    baris = bytearray()
    for y in range(tinggi):
        mentah = bgra[y * lebar * 4:(y + 1) * lebar * 4]
        rgb = bytearray(lebar * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = mentah[2::4], mentah[1::4], mentah[0::4]
        baris += bytes(1) + rgb

    def potongan(jenis: bytes, isi: bytes) -> bytes:
        return (struct.pack(">I", len(isi)) + jenis + isi
                + struct.pack(">I", zlib.crc32(jenis + isi) & 0xFFFFFFFF))

    lokasi.write_bytes(TANDA_PNG
                       + potongan(b"IHDR", struct.pack(">IIBBBBB", lebar, tinggi, 8, 2, 0, 0, 0))
                       + potongan(b"IDAT", zlib.compress(bytes(baris), 9))
                       + potongan(b"IEND", b""))


def _siapkan_winapi():
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    h = ctypes.c_void_p
    for f in (user32.GetWindowDC, gdi32.CreateCompatibleDC, gdi32.CreateCompatibleBitmap,
              gdi32.SelectObject):
        f.restype = h
    user32.GetWindowDC.argtypes = [h]
    gdi32.CreateCompatibleDC.argtypes = [h]
    gdi32.CreateCompatibleBitmap.argtypes = [h, ctypes.c_int, ctypes.c_int]
    gdi32.SelectObject.argtypes = [h, h]
    user32.PrintWindow.argtypes = [h, h, ctypes.c_uint]
    gdi32.GetDIBits.argtypes = [h, h, ctypes.c_uint, ctypes.c_uint, h, h, ctypes.c_uint]
    user32.ReleaseDC.argtypes = [h, h]
    gdi32.DeleteDC.argtypes = [h]
    gdi32.DeleteObject.argtypes = [h]
    return user32, gdi32


def tangkap(jendela, nama):
    """Gambar seluruh jendela (dengan judul dan menu) ke docs/panduan/gambar/<nama>.png.

    Windows kadang me-minimize jendela sesaat (mis. saat jendela lain aktif);
    jika ukurannya masih terlalu kecil, dicoba lagi.
    """
    user32, gdi32 = _siapkan_winapi()
    hwnd = ctypes.c_void_p(int(jendela.wm_frame(), 16))
    luar, nyata = wintypes.RECT(), wintypes.RECT()
    for _ in range(10):
        jendela.state("normal")
        jendela.deiconify()
        # Beri waktu tab yang baru dipilih untuk tergambar.
        for _ in range(15):
            jendela.update()
            time.sleep(0.1)
        user32.GetWindowRect(hwnd, ctypes.byref(luar))
        if luar.bottom - luar.top > 300:
            break
    else:
        raise RuntimeError(f"Jendela tidak tampil normal, gambar {nama} gagal diambil")
    # Batas jendela tanpa bayangan Windows 11 (DWMWA_EXTENDED_FRAME_BOUNDS = 9).
    ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(nyata), ctypes.sizeof(nyata))
    lebar, tinggi = luar.right - luar.left, luar.bottom - luar.top

    hdc = user32.GetWindowDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, lebar, tinggi)
    gdi32.SelectObject(mem, bmp)
    user32.PrintWindow(hwnd, mem, 2)  # PW_RENDERFULLCONTENT
    # BITMAPINFOHEADER: tinggi negatif = baris dari atas, 32 bit BGRA.
    info = ctypes.create_string_buffer(
        struct.pack("<IiiHHIIiiII", 40, lebar, -tinggi, 1, 32, 0, 0, 0, 0, 0, 0), 44)
    piksel = ctypes.create_string_buffer(lebar * tinggi * 4)
    gdi32.GetDIBits(mem, bmp, 0, tinggi, piksel, info, 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, hdc)

    # Buang bayangan di sekeliling jendela.
    kiri, atas = nyata.left - luar.left, nyata.top - luar.top
    lebar_n, tinggi_n = nyata.right - nyata.left, nyata.bottom - nyata.top
    data = piksel.raw
    potong = b"".join(
        data[((atas + y) * lebar + kiri) * 4:((atas + y) * lebar + kiri + lebar_n) * 4]
        for y in range(tinggi_n))
    lokasi = FOLDER_GAMBAR / f"{nama}.png"
    _tulis_png(lokasi, lebar_n, tinggi_n, potong)
    print("tersimpan:", lokasi.name)


def main():
    FOLDER_GAMBAR.mkdir(exist_ok=True)
    folder = Path(tempfile.mkdtemp())
    conn = buka_koneksi(folder / "kebun.db")
    pohon, ket = isi_contoh(conn)
    w = JendelaUtama(MasterService(conn), PeriodeService(conn), StokService(conn),
                     PanenService(conn), LaporanService(conn),
                     CadanganService(conn, folder / "cadangan"))
    w.geometry("+20+20")
    w.update()

    w.tab.select(w.layar_dashboard)
    for anak in w.layar_dashboard.isi.winfo_children():
        for halaman in anak.winfo_children():
            if getattr(halaman, "nama_jenis", None) == "Durian":
                anak.select(halaman)
    tangkap(w, "dashboard")

    panen = w.layar_panen
    w.tab.select(panen)
    panen.tgl.set_db("2026-10-13")
    panen._ganti_tanggal()
    p = pohon[1][0]
    panen.combo_jenis.pilih_id(p.get_varietas().get_jenis().get_id_jenis())
    panen._isi_varietas()
    panen.combo_varietas.pilih_id(p.get_varietas().get_id_varietas())
    panen._isi_pohon()
    panen.combo_pohon.pilih_id(p.get_id_pohon())
    panen.combo_keterangan.pilih_id(ket["Baik"].get_id_keterangan())
    panen._perbarui_info()
    set_entry(panen.entry_bobot, "2,4")
    tangkap(w, "catat_panen")

    w.tab.select(w.layar_stok)
    w.layar_stok.tabel.pilih_id(pohon[2][0].get_id_pohon())
    tangkap(w, "stok")

    w.tab.select(w.layar_periode)
    tangkap(w, "periode")

    w.tab.select(w.layar_master)
    sub = w.layar_master.sub_tab[2]
    w.nametowidget(sub.winfo_parent()).select(sub)
    tangkap(w, "master_pohon")

    w.destroy()
    conn.close()


if __name__ == "__main__":
    main()
