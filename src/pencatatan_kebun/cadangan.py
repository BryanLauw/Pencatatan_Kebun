"""Cadangan dan pemulihan database.

Memakai API backup SQLite (sqlite3.Connection.backup), yang aman walau database
sedang terbuka, bukan menyalin file biasa (salinan file bisa rusak jika ada
penulisan yang belum selesai).
"""
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from pencatatan_kebun.services.exception import ServiceException

log = logging.getLogger(__name__)

NAMA_FOLDER_OTOMATIS = "cadangan"
SIMPAN_OTOMATIS = 10
AWALAN_OTOMATIS = "kebun-"

# Tabel yang harus ada supaya file dianggap cadangan Pencatatan Kebun.
TABEL_WAJIB = {"jenis_tanaman", "varietas", "pohon", "keterangan_buah", "buah",
               "periode_panen", "stok_pohon"}

# Data selain data master, urut aman untuk dihapus (foreign key ON DELETE RESTRICT:
# buah dan stok dulu, baru periode).
TABEL_DATA_PANEN = ("buah", "stok_pohon", "periode_panen")


class CadanganGagalException(ServiceException):
    """Cadangan tidak bisa ditulis, mis. folder tidak bisa ditulisi atau
    flashdisk dicabut."""

    def __init__(self, lokasi: Path):
        super().__init__(f"Cadangan tidak bisa disimpan di {lokasi}. Pastikan folder atau "
                         "flashdisk tujuan bisa ditulisi, lalu coba lagi.")


class CadanganTidakValidException(ServiceException):
    """File yang dipilih untuk dipulihkan bukan cadangan Pencatatan Kebun atau rusak."""

    def __init__(self, lokasi: Path):
        super().__init__(f"File {lokasi.name} bukan cadangan Pencatatan Kebun atau sudah "
                         "rusak. Data tidak diubah.")


def nama_file_bawaan(waktu: datetime | None = None) -> str:
    """Nama usulan cadangan manual, mis. "Cadangan Kebun 14-10-2026.db"."""
    return f"Cadangan Kebun {(waktu or datetime.now()).strftime('%d-%m-%Y')}.db"


def simpan_cadangan(conn: sqlite3.Connection, tujuan: Path) -> None:
    """Salin seluruh isi database ke file tujuan (ditimpa jika sudah ada).

    Raises:
        CadanganGagalException: File tujuan tidak bisa ditulis.
    """
    tujuan = Path(tujuan)
    try:
        tujuan.parent.mkdir(parents=True, exist_ok=True)
        salinan = sqlite3.connect(tujuan)
        try:
            conn.backup(salinan)
        finally:
            salinan.close()
    except (OSError, sqlite3.Error) as e:
        raise CadanganGagalException(tujuan) from e


def cadangan_otomatis(conn: sqlite3.Connection, folder: Path, simpan: int = SIMPAN_OTOMATIS,
                      waktu: datetime | None = None) -> Path:
    """Buat cadangan bertanggal di folder, lalu hapus yang lama sehingga
    tersisa `simpan` cadangan terbaru.

    Returns:
        Lokasi cadangan yang baru dibuat.

    Raises:
        CadanganGagalException: File tidak bisa ditulis.
    """
    folder = Path(folder)
    lokasi = folder / f"{AWALAN_OTOMATIS}{(waktu or datetime.now()).strftime('%Y%m%d-%H%M%S')}.db"
    simpan_cadangan(conn, lokasi)
    # Nama berisi tanggal-waktu, jadi urutan nama = urutan waktu.
    lama = sorted(folder.glob(f"{AWALAN_OTOMATIS}*.db"))[:-simpan]
    for file in lama:
        try:
            file.unlink()
        except OSError:
            log.warning("Cadangan lama tidak bisa dihapus: %s", file)
    return lokasi


def daftar_cadangan_otomatis(folder: Path) -> list[Path]:
    """Cadangan otomatis di folder, terbaru lebih dulu."""
    return sorted(Path(folder).glob(f"{AWALAN_OTOMATIS}*.db"), reverse=True)


def _cek_cadangan(sumber: Path) -> None:
    """Pastikan file adalah database SQLite utuh berisi tabel Pencatatan Kebun.

    Raises:
        CadanganTidakValidException: Bukan SQLite, rusak, atau tabelnya tidak lengkap.
    """
    if not sumber.is_file():
        raise CadanganTidakValidException(sumber)
    try:
        cek = sqlite3.connect(f"{sumber.as_uri()}?mode=ro", uri=True)
        try:
            if cek.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise CadanganTidakValidException(sumber)
            tabel = {b[0] for b in cek.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            cek.close()
    except sqlite3.Error as e:
        raise CadanganTidakValidException(sumber) from e
    if not TABEL_WAJIB <= tabel:
        raise CadanganTidakValidException(sumber)


def pulihkan_cadangan(conn: sqlite3.Connection, sumber: Path) -> None:
    """Ganti seluruh isi database dengan isi file cadangan.

    File dicek dulu; jika tidak valid, database tidak diubah sama sekali.
    Pemanggil sebaiknya membuat cadangan otomatis lebih dulu, supaya data
    sebelum dipulihkan masih bisa dikembalikan.

    Raises:
        CadanganTidakValidException: File bukan cadangan Pencatatan Kebun atau rusak.
    """
    sumber = Path(sumber)
    _cek_cadangan(sumber)
    asal = sqlite3.connect(f"{sumber.as_uri()}?mode=ro", uri=True)
    try:
        asal.backup(conn)
    except sqlite3.Error as e:
        raise CadanganTidakValidException(sumber) from e
    finally:
        asal.close()


def nama_file_arsip(waktu: datetime | None = None) -> str:
    """Nama usulan arsip sebelum data panen dikosongkan, mis. "Arsip Kebun 14-10-2026.db"."""
    return f"Arsip Kebun {(waktu or datetime.now()).strftime('%d-%m-%Y')}.db"


def hitung_data_panen(conn: sqlite3.Connection) -> dict[str, int]:
    """Jumlah baris tiap tabel data panen, untuk ditampilkan di konfirmasi."""
    return {tabel: conn.execute(f"SELECT COUNT(*) FROM {tabel}").fetchone()[0]
            for tabel in TABEL_DATA_PANEN}


def kosongkan_data_panen(conn: sqlite3.Connection) -> None:
    """Hapus semua periode, stok, dan catatan buah; data master tetap.

    Penghapusan dalam satu transaksi (semua terhapus atau tidak sama sekali),
    lalu file database dipadatkan (VACUUM) supaya ukurannya ikut mengecil.
    """
    with conn:
        for tabel in TABEL_DATA_PANEN:
            conn.execute(f"DELETE FROM {tabel}")
    conn.execute("VACUUM")


class CadanganService:
    """Cadangan untuk ui: simpan manual, cadangan otomatis, dan pulihkan.

    Args:
        conn: Koneksi database aplikasi.
        folder_otomatis: Folder cadangan otomatis, mis. %APPDATA%\\PencatatanKebun\\cadangan.
    """

    def __init__(self, conn: sqlite3.Connection, folder_otomatis: Path):
        self.conn = conn
        self.folder_otomatis = Path(folder_otomatis)

    def simpan(self, tujuan: Path) -> None:
        """Cadangan manual ke file pilihan pengguna (mis. di flashdisk)."""
        simpan_cadangan(self.conn, tujuan)

    def otomatis(self) -> Path:
        """Cadangan otomatis bertanggal; hanya SIMPAN_OTOMATIS terbaru yang disimpan."""
        return cadangan_otomatis(self.conn, self.folder_otomatis)

    def pulihkan(self, sumber: Path) -> Path:
        """Ganti data dengan isi cadangan, setelah lebih dulu mencadangkan data
        sekarang secara otomatis (supaya pemulihan yang keliru bisa dibatalkan).

        Returns:
            Lokasi cadangan otomatis data sebelum dipulihkan.

        Raises:
            CadanganTidakValidException: File bukan cadangan yang valid (dicek
                sebelum apa pun diubah).
            CadanganGagalException: Cadangan otomatis gagal dibuat; data tidak diubah.
        """
        _cek_cadangan(Path(sumber))
        sebelum = self.otomatis()
        pulihkan_cadangan(self.conn, sumber)
        return sebelum

    def hitung_data_panen(self) -> dict[str, int]:
        """Jumlah periode, stok, dan buah yang akan terhapus oleh arsipkan()."""
        return hitung_data_panen(self.conn)

    def arsipkan(self, tujuan: Path) -> None:
        """Simpan semua data ke file arsip, lalu kosongkan data panen (periode,
        stok, buah); data master tetap untuk dipakai periode berikutnya.

        Data baru dihapus setelah arsip berhasil ditulis dan dicek, serta
        cadangan otomatis dibuat (jaga-jaga file arsip hilang).

        Raises:
            CadanganGagalException: Arsip atau cadangan otomatis gagal dibuat;
                data tidak diubah.
        """
        tujuan = Path(tujuan)
        simpan_cadangan(self.conn, tujuan)
        try:
            _cek_cadangan(tujuan)
        except CadanganTidakValidException as e:
            raise CadanganGagalException(tujuan) from e
        self.otomatis()
        kosongkan_data_panen(self.conn)
