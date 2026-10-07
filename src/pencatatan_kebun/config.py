import os
from pathlib import Path

NAMA_APLIKASI = "PencatatanKebun"
NAMA_FILE_DB = "kebun.db"

# Format tanggal untuk tampilan di ui (DD-MM-YYYY). Di database dan model,
# tanggal selalu disimpan sebagai teks YYYY-MM-DD.
FORMAT_TANGGAL_TAMPIL = "%d-%m-%Y"


def folder_data() -> Path:
    """Folder data pengguna.

    Returns:
        Path folder, mis. C:\\Users\\Ayah\\AppData\\Roaming\\PencatatanKebun.
    """
    dasar = os.environ.get("APPDATA") or Path.home()
    return Path(dasar) / NAMA_APLIKASI


def lokasi_db() -> Path:
    """Path file database aplikasi.

    Returns:
        Path file, mis. ...\\AppData\\Roaming\\PencatatanKebun\\kebun.db.
    """
    return folder_data() / NAMA_FILE_DB
