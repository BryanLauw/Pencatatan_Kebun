import logging
from pathlib import Path

from pencatatan_kebun.cadangan import NAMA_FOLDER_OTOMATIS, CadanganService
from pencatatan_kebun.config import lokasi_db
from pencatatan_kebun.db.koneksi import buka_koneksi
from pencatatan_kebun.services.laporan import LaporanService
from pencatatan_kebun.services.master import MasterService
from pencatatan_kebun.services.panen import PanenService
from pencatatan_kebun.services.periode import PeriodeService
from pencatatan_kebun.services.stok import StokService
from pencatatan_kebun.ui.jendela_utama import JendelaUtama

NAMA_FILE_LOG = "kebun.log"

log = logging.getLogger(__name__)


def _pasang_log(folder: Path) -> logging.Handler:
    """Catat error ke file log di folder database.

    Returns:
        Handler yang dipasang, untuk dilepas lagi saat aplikasi selesai.
    """
    handler = logging.FileHandler(folder / NAMA_FILE_LOG, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    return handler


def _cadangan_saat_tutup(cadangan: CadanganService) -> None:
    """Cadangan otomatis setelah jendela ditutup. Kegagalan hanya dicatat di
    log, supaya aplikasi tetap bisa ditutup."""
    try:
        cadangan.otomatis()
    except Exception:
        log.exception("Cadangan otomatis gagal")


def jalankan(lokasi=None) -> None:
    """Jalankan aplikasi: buka database, tampilkan ui, lalu tutup koneksi.

    Setelah jendela ditutup normal, dibuat cadangan otomatis di folder
    "cadangan" di samping database. Koneksi selalu ditutup saat aplikasi
    selesai, termasuk jika terjadi error.

    Args:
        lokasi: Path database. Jika None, dipakai lokasi_db() di folder data
            pengguna. Diisi lain (mis. folder sementara) untuk tes.
    """
    lokasi = Path(lokasi if lokasi is not None else lokasi_db())
    conn = buka_koneksi(lokasi)
    handler = _pasang_log(lokasi.parent)
    cadangan = CadanganService(conn, lokasi.parent / NAMA_FOLDER_OTOMATIS)
    try:
        jendela = JendelaUtama(master_service=MasterService(conn),
                               periode_service=PeriodeService(conn),
                               stok_service=StokService(conn),
                               panen_service=PanenService(conn),
                               laporan_service=LaporanService(conn),
                               cadangan_service=cadangan)
        jendela.mainloop()
        _cadangan_saat_tutup(cadangan)
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()
        conn.close()
