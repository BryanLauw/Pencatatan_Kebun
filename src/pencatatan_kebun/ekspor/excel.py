"""Ekspor laporan satu periode panen ke file Excel (.xlsx).

Format mengikuti Excel lama pemilik kebun (satu baris per pohon, satu kolom per
tanggal panen), ditambah ringkasan per varietas dan keterangan, serta daftar
setiap buah. Satu file per periode:

- "Ringkasan": total per jenis.
- Satu sheet per jenis: tabel per pohon, lalu ringkasan per varietas.
- "Catatan buah": setiap buah (tanggal, jenis, varietas, pohon, keterangan, bobot).

Data dasar (stok, jumlah buah per tanggal, kg, bobot tiap buah) ditulis sebagai
angka; semua hasil hitungan berupa rumus, seperti Excel lama, jadi total ikut
berubah jika angka dasar diubah di Excel.
"""
import re
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties
from openpyxl.worksheet.worksheet import Worksheet

from pencatatan_kebun.models import PeriodePanen
from pencatatan_kebun.services.exception import ServiceException
from pencatatan_kebun.services.laporan import LaporanService
from pencatatan_kebun.services.master import MasterService
from pencatatan_kebun.services.panen import PanenService
from pencatatan_kebun.services.stok import StokService
from pencatatan_kebun.ui.format import tanggal_ke_tampil

SHEET_RINGKASAN = "Ringkasan"
SHEET_BUAH = "Catatan buah"
FORMAT_TANGGAL = "dd-mm-yyyy"
FORMAT_TANGGAL_KOLOM = "dd-mm"
FORMAT_KG = "0.00"
FORMAT_PERSEN = "0.0%"

_TEBAL = Font(bold=True)
_JUDUL = Font(bold=True, size=14)
_LATAR_HEADER = PatternFill("solid", fgColor="E7E6E1")
_LATAR_TOTAL = PatternFill("solid", fgColor="F2F1EC")
_LATAR_MINUS = PatternFill("solid", fgColor="FDE2E1")
_GARIS = Side(style="thin", color="B8B8B8")
_KOTAK = Border(left=_GARIS, right=_GARIS, top=_GARIS, bottom=_GARIS)
_TENGAH = Alignment(horizontal="center", vertical="center", wrap_text=True)

# Kolom tetap di sheet jenis (A-E); kolom tanggal mulai di F.
_KOLOM_AWAL = ("No", "Varietas", "No. pohon", "Tgl hitung", "Stok")
_BARIS_HEADER = 3            # header 2 baris: baris 3 dan 4
_BARIS_DATA = 5


class EksporGagalException(ServiceException):
    """File Excel tidak bisa ditulis, biasanya karena sedang dibuka di Excel."""

    def __init__(self, lokasi: Path):
        super().__init__(f"File {lokasi.name} tidak bisa disimpan. Jika file itu sedang "
                         "dibuka di Excel, tutup dulu lalu coba lagi.")


# ---- data (tanpa openpyxl) ----

def kumpulkan_data(master: MasterService, stok: StokService, panen: PanenService,
                   laporan: LaporanService, periode: PeriodePanen) -> dict:
    """Susun semua angka laporan satu periode.

    Returns:
        {"periode": PeriodePanen,
         "jenis": [{"nama": str, "tanggal": [date], "keterangan": [str],
                    "pohon": [{"varietas", "nomor", "tgl_hitung", "stok",
                               "per_tanggal": {date: int}, "panen", "kg",
                               "per_keterangan": {str: int}}],
                    "varietas": [{"nama", "bobot_min", "bobot_max"}],
                    "ringkasan": hasil LaporanService.ringkasan_jenis}],
         "buah": [{"tanggal": date, "jenis", "varietas", "nomor", "keterangan", "bobot"}]}

        Hanya jenis yang punya stok atau panen di periode itu (sama dengan
        Dashboard), tetapi semua pohon jenis itu ikut ditampilkan.
    """
    id_periode = periode.get_id_periode()
    stok_pohon = {d["stok"].get_pohon().get_id_pohon(): d["stok"]
                  for d in stok.daftar_stok_periode(id_periode)}
    semua_buah = panen.daftar_buah_per_periode(id_periode)
    dashboard = laporan.dashboard(id_periode)

    hasil_jenis = []
    for nama_jenis, data_jenis in dashboard["per_jenis"].items():
        id_jenis = data_jenis["jenis"].get_id_jenis()
        daftar_pohon = sorted(
            (p for p in master.daftar_pohon()
             if p.get_varietas().get_jenis().get_id_jenis() == id_jenis),
            key=lambda p: (p.get_varietas().get_nama_varietas().casefold(), p.get_nomor_pohon()))
        buah_jenis = [b for b in semua_buah
                      if b.get_pohon().get_varietas().get_jenis().get_id_jenis() == id_jenis]

        baris_pohon = []
        for pohon in daftar_pohon:
            buah = [b for b in buah_jenis if b.get_pohon().get_id_pohon() == pohon.get_id_pohon()]
            per_tanggal: dict[date, int] = {}
            per_keterangan: dict[str, int] = {}
            for b in buah:
                tgl = date.fromisoformat(b.get_tanggal_panen())
                per_tanggal[tgl] = per_tanggal.get(tgl, 0) + 1
                nama_ket = b.get_keterangan().get_nama_keterangan()
                per_keterangan[nama_ket] = per_keterangan.get(nama_ket, 0) + 1
            s = stok_pohon.get(pohon.get_id_pohon())
            baris_pohon.append({
                "varietas": pohon.get_varietas().get_nama_varietas(),
                "nomor": pohon.get_nomor_pohon(),
                "tgl_hitung": date.fromisoformat(s.get_tanggal_hitung()) if s else None,
                "stok": s.get_jumlah_buah() if s else None,
                "per_tanggal": per_tanggal,
                "panen": len(buah),
                "kg": sum(b.get_bobot() for b in buah),
                "per_keterangan": per_keterangan,
            })

        varietas = []
        for nama in dict.fromkeys(p["varietas"] for p in baris_pohon):
            v = data_jenis["per_varietas"].get(nama)
            varietas.append({"nama": nama, "bobot_min": v["bobot_min"] if v else None,
                             "bobot_max": v["bobot_max"] if v else None})

        hasil_jenis.append({
            "nama": nama_jenis,
            "tanggal": sorted({date.fromisoformat(b.get_tanggal_panen()) for b in buah_jenis}),
            "keterangan": list(data_jenis["ringkasan"]["per_keterangan"]),
            "pohon": baris_pohon,
            "varietas": varietas,
            "ringkasan": {"ringkasan": data_jenis["ringkasan"],
                          "per_varietas": data_jenis["per_varietas"]},
        })

    buah = sorted((
        {"tanggal": date.fromisoformat(b.get_tanggal_panen()),
         "jenis": b.get_pohon().get_varietas().get_jenis().get_nama_jenis(),
         "varietas": b.get_pohon().get_varietas().get_nama_varietas(),
         "nomor": b.get_pohon().get_nomor_pohon(),
         "keterangan": b.get_keterangan().get_nama_keterangan(),
         "bobot": b.get_bobot()} for b in semua_buah),
        key=lambda b: (b["tanggal"], b["jenis"].casefold(), b["varietas"].casefold(), b["nomor"]))
    return {"periode": periode, "jenis": hasil_jenis, "buah": buah}


def nama_file_bawaan(periode: PeriodePanen, hari_ini: date | None = None) -> str:
    """Nama file usulan, mis. "Laporan Panen Raya 2026 14-10-2026.xlsx"."""
    tanggal = (hari_ini or date.today()).strftime("%d-%m-%Y")
    nama = " ".join(re.sub(r'[\\/:*?"<>|]+', " ", periode.get_nama()).split())
    return f"Laporan Panen {nama} {tanggal}.xlsx"


def nama_sheet_aman(nama: str, terpakai: set[str]) -> str:
    """Nama sheet yang diterima Excel: tanpa []:*?/\\, maks 31 karakter, unik
    (tanpa membedakan huruf besar/kecil)."""
    dasar = re.sub(r"[\[\]:*?/\\]", " ", nama).strip(" '") or "Jenis"
    dasar = dasar[:31]
    hasil, nomor = dasar, 2
    while hasil.casefold() in terpakai:
        akhiran = f" ({nomor})"
        hasil, nomor = dasar[:31 - len(akhiran)] + akhiran, nomor + 1
    terpakai.add(hasil.casefold())
    return hasil


# ---- penulisan Excel ----

def _teks_rumus(teks: str) -> str:
    """Teks sebagai literal string di rumus Excel ("..." dengan " digandakan)."""
    return '"' + teks.replace('"', '""') + '"'


def _rujukan_sheet(nama: str) -> str:
    """Nama sheet di rumus, mis. 'Catatan buah'!"""
    return "'" + nama.replace("'", "''") + "'!"


def _sel(ws: Worksheet, baris: int, kolom: int, nilai=None, format_angka: str | None = None,
         font: Font | None = None, latar: PatternFill | None = None, kotak: bool = True):
    sel = ws.cell(row=baris, column=kolom, value=nilai)
    if format_angka:
        sel.number_format = format_angka
    if font:
        sel.font = font
    if latar:
        sel.fill = latar
    if kotak:
        sel.border = _KOTAK
    return sel


def _header(ws: Worksheet, baris: int, kolom: int, teks, sampai_baris: int | None = None,
            sampai_kolom: int | None = None, format_angka: str | None = None) -> None:
    """Sel header (abu-abu, tebal, di tengah), digabung jika perlu."""
    sampai_baris, sampai_kolom = sampai_baris or baris, sampai_kolom or kolom
    for b in range(baris, sampai_baris + 1):
        for k in range(kolom, sampai_kolom + 1):
            _sel(ws, b, k, font=_TEBAL, latar=_LATAR_HEADER).alignment = _TENGAH
    sel = ws.cell(row=baris, column=kolom, value=teks)
    if format_angka:
        sel.number_format = format_angka
    if (sampai_baris, sampai_kolom) != (baris, kolom):
        ws.merge_cells(start_row=baris, start_column=kolom, end_row=sampai_baris,
                       end_column=sampai_kolom)


def _atur_cetak(ws: Worksheet) -> None:
    """Saat dicetak: lanskap, semua kolom muat satu halaman ke samping."""
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0


def _lebar_kolom(ws: Worksheet, lebar: dict[int, float]) -> None:
    for kolom, ukuran in lebar.items():
        ws.column_dimensions[get_column_letter(kolom)].width = ukuran


def _tulis_buah(ws: Worksheet, buah: list[dict]) -> None:
    judul = ("Tanggal", "Jenis", "Varietas", "No. pohon", "Keterangan", "Bobot (kg)")
    for k, teks in enumerate(judul, start=1):
        _header(ws, 1, k, teks)
    for i, b in enumerate(buah, start=2):
        _sel(ws, i, 1, b["tanggal"], FORMAT_TANGGAL)
        _sel(ws, i, 2, b["jenis"])
        _sel(ws, i, 3, b["varietas"])
        _sel(ws, i, 4, b["nomor"])
        _sel(ws, i, 5, b["keterangan"])
        _sel(ws, i, 6, b["bobot"], FORMAT_KG)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:F{max(1, len(buah)) + 1}"
    _lebar_kolom(ws, {1: 13, 2: 14, 3: 18, 4: 10, 5: 14, 6: 11})


def _tulis_jenis(ws: Worksheet, jenis: dict, periode: PeriodePanen) -> int:
    """Tulis satu sheet jenis.

    Returns:
        Nomor baris Total di tabel per pohon (dirujuk sheet Ringkasan).
    """
    tanggal, keterangan, pohon = jenis["tanggal"], jenis["keterangan"], jenis["pohon"]
    k_tgl = len(_KOLOM_AWAL) + 1                    # kolom tanggal pertama (F)
    k_panen = k_tgl + len(tanggal)
    k_sisa, k_kg, k_rata = k_panen + 1, k_panen + 2, k_panen + 3
    k_ket = k_rata + 1
    k_akhir = k_ket + len(keterangan) - 1 if keterangan else k_rata
    h = _BARIS_HEADER
    awal, akhir = _BARIS_DATA, _BARIS_DATA + max(len(pohon), 1) - 1
    huruf = get_column_letter
    buah = _rujukan_sheet(SHEET_BUAH)

    selesai = periode.get_tanggal_selesai()
    ws.cell(row=1, column=1, value=(
        f"Stok {jenis['nama']} - Periode {periode.get_nama()} "
        f"({tanggal_ke_tampil(periode.get_tanggal_mulai())} s.d. "
        f"{tanggal_ke_tampil(selesai) if selesai else 'sekarang'})")).font = _JUDUL

    # Header 2 baris.
    for k, teks in enumerate(_KOLOM_AWAL, start=1):
        _header(ws, h, k, teks, sampai_baris=h + 1)
    if tanggal:
        _header(ws, h, k_tgl, "Tanggal panen (jumlah buah)", sampai_kolom=k_panen - 1)
        for i, tgl in enumerate(tanggal):
            _header(ws, h + 1, k_tgl + i, tgl, format_angka=FORMAT_TANGGAL_KOLOM)
    _header(ws, h, k_panen, "Jumlah", sampai_kolom=k_rata)
    for k, teks in ((k_panen, "Panen"), (k_sisa, "Sisa"), (k_kg, "kg"), (k_rata, "Rata-rata kg")):
        _header(ws, h + 1, k, teks)
    if keterangan:
        _header(ws, h, k_ket, "Keterangan (jumlah buah)", sampai_kolom=k_akhir)
        for i, nama in enumerate(keterangan):
            _header(ws, h + 1, k_ket + i, nama)

    # Satu baris per pohon.
    for i, p in enumerate(pohon):
        b = awal + i
        _sel(ws, b, 1, i + 1)
        _sel(ws, b, 2, p["varietas"])
        _sel(ws, b, 3, p["nomor"])
        _sel(ws, b, 4, p["tgl_hitung"], FORMAT_TANGGAL)
        _sel(ws, b, 5, p["stok"])
        for j, tgl in enumerate(tanggal):
            _sel(ws, b, k_tgl + j, p["per_tanggal"].get(tgl))
        panen = (f"=SUM({huruf(k_tgl)}{b}:{huruf(k_panen - 1)}{b})" if tanggal else 0)
        _sel(ws, b, k_panen, panen)
        _sel(ws, b, k_sisa, f"=E{b}-{huruf(k_panen)}{b}")
        _sel(ws, b, k_kg, p["kg"] or None, FORMAT_KG)
        _sel(ws, b, k_rata, f'=IF({huruf(k_panen)}{b}=0,"",{huruf(k_kg)}{b}/{huruf(k_panen)}{b})',
             FORMAT_KG)
        for j, nama in enumerate(keterangan):
            _sel(ws, b, k_ket + j, p["per_keterangan"].get(nama))

    # Baris Total dan total kg per tanggal.
    total = akhir + 1
    _sel(ws, total, 1, latar=_LATAR_TOTAL)
    _sel(ws, total, 2, "Total", font=_TEBAL, latar=_LATAR_TOTAL)
    for k in range(3, k_akhir + 1):
        if k in (3, 4):
            _sel(ws, total, k, latar=_LATAR_TOTAL)
        elif k == k_rata:
            _sel(ws, total, k, f'=IF({huruf(k_panen)}{total}=0,"",'
                               f'{huruf(k_kg)}{total}/{huruf(k_panen)}{total})',
                 FORMAT_KG, _TEBAL, _LATAR_TOTAL)
        else:
            _sel(ws, total, k, f"=SUM({huruf(k)}{awal}:{huruf(k)}{akhir})",
                 FORMAT_KG if k == k_kg else None, _TEBAL, _LATAR_TOTAL)
    if tanggal:
        kg = total + 1
        _sel(ws, kg, 2, "Total kg per tanggal", font=_TEBAL, latar=_LATAR_TOTAL)
        for k in (1, 3, 4, 5):
            _sel(ws, kg, k, latar=_LATAR_TOTAL)
        for j in range(len(tanggal)):
            kolom = huruf(k_tgl + j)
            _sel(ws, kg, k_tgl + j,
                 f"=SUMIFS({buah}$F:$F,{buah}$B:$B,{_teks_rumus(jenis['nama'])},"
                 f"{buah}$A:$A,{kolom}${h + 1})", FORMAT_KG, _TEBAL, _LATAR_TOTAL)

    # Sisa negatif (panen melebihi stok) merah muda; ikut berubah jika diedit.
    ws.conditional_formatting.add(
        f"{huruf(k_sisa)}{awal}:{huruf(k_sisa)}{akhir}",
        CellIsRule(operator="lessThan", formula=["0"], fill=_LATAR_MINUS))

    _tulis_ringkasan_varietas(ws, jenis, total + 4, awal, akhir,
                              {"stok": 5, "panen": k_panen, "kg": k_kg, "ket": k_ket})

    ws.freeze_panes = ws.cell(row=_BARIS_DATA, column=k_tgl)
    lebar = {1: 5, 2: 18, 3: 9, 4: 12, 5: 7, k_panen: 8, k_sisa: 7, k_kg: 9, k_rata: 11}
    lebar.update({k_tgl + j: 7 for j in range(len(tanggal))})
    lebar.update({k_ket + j: 10 for j in range(len(keterangan))})
    _lebar_kolom(ws, lebar)
    return total


def _tulis_ringkasan_varietas(ws: Worksheet, jenis: dict, baris: int, awal: int, akhir: int,
                              kolom_pohon: dict) -> None:
    """Ringkasan per varietas di bawah tabel pohon, semuanya rumus SUMIF ke
    tabel pohon (dan SUMIFS ke Catatan buah untuk kg per keterangan)."""
    huruf = get_column_letter
    keterangan = jenis["keterangan"]
    buah = _rujukan_sheet(SHEET_BUAH)
    ws.cell(row=baris, column=1, value=f"Ringkasan per varietas {jenis['nama']}").font = _JUDUL
    h = baris + 1
    judul = ("Varietas", "Stok", "Panen", "Sisa", "Total kg", "Rata-rata kg", "Min kg", "Maks kg")
    for k, teks in enumerate(judul, start=2):
        _header(ws, h, k, teks, sampai_baris=h + 1)
    k_ket = 2 + len(judul)
    for i, nama in enumerate(keterangan):
        k = k_ket + i * 4
        _header(ws, h, k, nama, sampai_kolom=k + 3)
        for j, teks in enumerate(("Buah", "%", "kg", "Rata-rata kg")):
            _header(ws, h + 1, k + j, teks)

    def sumif(kolom: int, b: int) -> str:
        return (f"=SUMIF($B${awal}:$B${akhir},$B{b},"
                f"{huruf(kolom)}${awal}:{huruf(kolom)}${akhir})")

    pertama = h + 2
    for i, v in enumerate(jenis["varietas"]):
        b = pertama + i
        _sel(ws, b, 2, v["nama"])
        _sel(ws, b, 3, sumif(kolom_pohon["stok"], b))
        _sel(ws, b, 4, sumif(kolom_pohon["panen"], b))
        _sel(ws, b, 5, f"=C{b}-D{b}")
        _sel(ws, b, 6, sumif(kolom_pohon["kg"], b), FORMAT_KG)
        _sel(ws, b, 7, f'=IF(D{b}=0,"",F{b}/D{b})', FORMAT_KG)
        _sel(ws, b, 8, v["bobot_min"], FORMAT_KG)
        _sel(ws, b, 9, v["bobot_max"], FORMAT_KG)
        for j, nama in enumerate(keterangan):
            k = k_ket + j * 4
            jml, kg = huruf(k), huruf(k + 2)
            _sel(ws, b, k, sumif(kolom_pohon["ket"] + j, b))
            _sel(ws, b, k + 1, f'=IF($D{b}=0,"",{jml}{b}/$D{b})', FORMAT_PERSEN)
            _sel(ws, b, k + 2, f"=SUMIFS({buah}$F:$F,{buah}$B:$B,{_teks_rumus(jenis['nama'])},"
                               f"{buah}$C:$C,$B{b},{buah}$E:$E,{_teks_rumus(nama)})", FORMAT_KG)
            _sel(ws, b, k + 3, f'=IF({jml}{b}=0,"",{kg}{b}/{jml}{b})', FORMAT_KG)

    terakhir = pertama + max(len(jenis["varietas"]), 1) - 1
    t = terakhir + 1

    def total(kolom: int, rumus: str, format_angka: str | None = None) -> None:
        _sel(ws, t, kolom, rumus, format_angka, _TEBAL, _LATAR_TOTAL)

    total(2, f"Total {jenis['nama']}")
    for k, f in ((3, None), (4, None), (5, None), (6, FORMAT_KG)):
        total(k, f"=SUM({huruf(k)}{pertama}:{huruf(k)}{terakhir})", f)
    total(7, f'=IF(D{t}=0,"",F{t}/D{t})', FORMAT_KG)
    total(8, f"=IF(COUNT(H{pertama}:H{terakhir})=0,\"\",MIN(H{pertama}:H{terakhir}))", FORMAT_KG)
    total(9, f"=IF(COUNT(I{pertama}:I{terakhir})=0,\"\",MAX(I{pertama}:I{terakhir}))", FORMAT_KG)
    for j in range(len(keterangan)):
        k = k_ket + j * 4
        jml, kg = huruf(k), huruf(k + 2)
        total(k, f"=SUM({jml}{pertama}:{jml}{terakhir})")
        total(k + 1, f'=IF($D{t}=0,"",{jml}{t}/$D{t})', FORMAT_PERSEN)
        total(k + 2, f"=SUM({kg}{pertama}:{kg}{terakhir})", FORMAT_KG)
        total(k + 3, f'=IF({jml}{t}=0,"",{kg}{t}/{jml}{t})', FORMAT_KG)


def _tulis_ringkasan(ws: Worksheet, data: dict, sheet_jenis: list[tuple[str, int, int]]) -> None:
    """Sheet pertama: total per jenis, merujuk baris Total di tiap sheet jenis.

    Args:
        sheet_jenis: (nama sheet, baris Total, kolom Panen) per jenis.
    """
    periode = data["periode"]
    selesai = periode.get_tanggal_selesai()
    ws.cell(row=1, column=1, value=f"Laporan Panen - Periode {periode.get_nama()}").font = _JUDUL
    ws.cell(row=2, column=1, value=(
        f"{tanggal_ke_tampil(periode.get_tanggal_mulai())} s.d. "
        f"{tanggal_ke_tampil(selesai) if selesai else 'sekarang'}"))
    ws.cell(row=3, column=1, value=f"Diekspor {date.today().strftime('%d-%m-%Y')}")

    judul = ("Jenis", "Pohon dihitung", "Stok", "Panen", "Sisa", "Total kg", "Rata-rata kg/buah")
    for k, teks in enumerate(judul, start=1):
        _header(ws, 5, k, teks)
    huruf = get_column_letter
    for i, (nama, baris_total, k_panen) in enumerate(sheet_jenis):
        b = 6 + i
        s = _rujukan_sheet(nama)
        _sel(ws, b, 1, nama)
        _sel(ws, b, 2, f"=COUNT({s}E{_BARIS_DATA}:E{baris_total - 1})")
        _sel(ws, b, 3, f"={s}E{baris_total}")
        _sel(ws, b, 4, f"={s}{huruf(k_panen)}{baris_total}")
        _sel(ws, b, 5, f"={s}{huruf(k_panen + 1)}{baris_total}")
        _sel(ws, b, 6, f"={s}{huruf(k_panen + 2)}{baris_total}", FORMAT_KG)
        _sel(ws, b, 7, f'=IF(D{b}=0,"",F{b}/D{b})', FORMAT_KG)
    if not sheet_jenis:
        ws.cell(row=6, column=1, value="Belum ada stok atau panen di periode ini.")
    _lebar_kolom(ws, {1: 18, 2: 15, 3: 9, 4: 9, 5: 9, 6: 11, 7: 18})


def tulis_excel(data: dict, lokasi: Path) -> None:
    """Tulis laporan (hasil kumpulkan_data) ke file .xlsx.

    Raises:
        EksporGagalException: File tidak bisa ditulis (mis. sedang dibuka di Excel).
    """
    wb = Workbook()
    ringkasan = wb.active
    ringkasan.title = SHEET_RINGKASAN
    terpakai = {SHEET_RINGKASAN.casefold(), SHEET_BUAH.casefold()}

    sheet_jenis = []
    for jenis in data["jenis"]:
        nama = nama_sheet_aman(jenis["nama"], terpakai)
        baris_total = _tulis_jenis(wb.create_sheet(nama), jenis, data["periode"])
        sheet_jenis.append((nama, baris_total, len(_KOLOM_AWAL) + 1 + len(jenis["tanggal"])))
    _tulis_buah(wb.create_sheet(SHEET_BUAH), data["buah"])
    _tulis_ringkasan(ringkasan, data, sheet_jenis)
    for ws in wb.worksheets:
        _atur_cetak(ws)

    # Hasil rumus dihitung Excel saat file dibuka.
    wb.calculation = CalcProperties(fullCalcOnLoad=True)
    try:
        wb.save(lokasi)
    except PermissionError as e:
        raise EksporGagalException(Path(lokasi)) from e
