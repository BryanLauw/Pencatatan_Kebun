import os
from pathlib import Path

NAMA_APLIKASI = "PencatatanKebun"
NAMA_FILE_DB = "kebun.db"

# Database disimpan YYYY-MM-DD; format ini hanya untuk tampilan di ui.
FORMAT_TANGGAL_TAMPIL = "%d-%m-%Y"


def folder_data() -> Path:
    """Folder data pengguna, mis. C:\\Users\\Ayah\\AppData\\Roaming\\PencatatanKebun."""
    dasar = os.environ.get("APPDATA") or Path.home()
    return Path(dasar) / NAMA_APLIKASI


def lokasi_db() -> Path:
    return folder_data() / NAMA_FILE_DB
