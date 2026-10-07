import uuid
from typing import Optional
from datetime import datetime


class JenisTanaman:
    """Jenis tanaman, mis. "Durian" atau "Mangga". Data master.

    Args:
        nama_jenis: Nama jenis tanaman.
        deskripsi: Keterangan tambahan, boleh kosong.
        id_jenis: Id jenis. Dibuat otomatis (UUID) jika tidak diisi, dan tidak
            punya setter.
    """

    def __init__(self, nama_jenis: str, deskripsi: str = "", id_jenis: Optional[str] = None):
        self.id_jenis = id_jenis or str(uuid.uuid4())
        self.nama_jenis = nama_jenis
        self.deskripsi = deskripsi

    def get_id_jenis(self):
        return self.id_jenis

    def set_nama_jenis(self, nama_jenis: str):
        self.nama_jenis = nama_jenis

    def get_nama_jenis(self):
        return self.nama_jenis

    def set_deskripsi(self, deskripsi: str):
        self.deskripsi = deskripsi

    def get_deskripsi(self):
        return self.deskripsi


class Varietas:
    """Varietas di dalam satu jenis tanaman, mis. "Musang King" untuk Durian. Data master.

    Args:
        nama_varietas: Nama varietas. Hanya unik di dalam jenisnya.
        jenis: Objek JenisTanaman pemilik varietas.
        deskripsi: Keterangan tambahan, boleh kosong.
        id_varietas: Id varietas. Dibuat otomatis (UUID) jika tidak diisi, dan
            tidak punya setter.
    """

    def __init__(self, nama_varietas: str, jenis: JenisTanaman, deskripsi: str = "",
                 id_varietas: Optional[str] = None):
        self.id_varietas = id_varietas or str(uuid.uuid4())
        self.nama_varietas = nama_varietas
        self.jenis = jenis
        self.deskripsi = deskripsi

    def get_id_varietas(self):
        return self.id_varietas

    def set_nama_varietas(self, nama_varietas: str):
        self.nama_varietas = nama_varietas

    def get_nama_varietas(self):
        return self.nama_varietas

    def set_jenis(self, jenis: JenisTanaman):
        self.jenis = jenis

    def get_jenis(self):
        return self.jenis

    def set_deskripsi(self, deskripsi: str):
        self.deskripsi = deskripsi

    def get_deskripsi(self):
        return self.deskripsi


class Pohon:
    """Satu pohon di kebun, dikenali dari nomornya. Data master.

    Pohon tidak terhubung ke jenis tanaman: satu pohon boleh menghasilkan buah
    dari varietas apa pun (mis. lewat stek).

    Args:
        nomor_pohon: Nomor pohon di kebun.
        id_pohon: Id pohon. Dibuat otomatis (UUID) jika tidak diisi, dan tidak
            punya setter.
    """

    def __init__(self, nomor_pohon: int, id_pohon: Optional[str] = None):
        self.id_pohon = id_pohon or str(uuid.uuid4())
        self.nomor_pohon = nomor_pohon

    def get_id_pohon(self):
        return self.id_pohon

    def set_nomor_pohon(self, nomor_pohon: int):
        self.nomor_pohon = nomor_pohon

    def get_nomor_pohon(self):
        return self.nomor_pohon


class KeteranganBuah:
    """Kondisi buah saat dipanen, mis. "Baik" atau "Busuk". Data master.

    Args:
        nama_keterangan: Nama keterangan.
        deskripsi: Penjelasan tambahan, boleh kosong.
        id_keterangan: Id keterangan. Dibuat otomatis (UUID) jika tidak diisi,
            dan tidak punya setter.
    """

    def __init__(self, nama_keterangan: str, deskripsi: str = "",
                 id_keterangan: Optional[str] = None):
        self.id_keterangan = id_keterangan or str(uuid.uuid4())
        self.nama_keterangan = nama_keterangan
        self.deskripsi = deskripsi

    def get_id_keterangan(self):
        return self.id_keterangan

    def set_nama_keterangan(self, nama_keterangan: str):
        self.nama_keterangan = nama_keterangan

    def get_nama_keterangan(self):
        return self.nama_keterangan

    def set_deskripsi(self, deskripsi: str):
        self.deskripsi = deskripsi

    def get_deskripsi(self):
        return self.deskripsi


class Buah:
    """Satu catatan buah hasil panen.

    Jenis tanaman diketahui lewat varietas.get_jenis().

    Args:
        pohon: Objek Pohon asal buah.
        varietas: Objek Varietas buah.
        bobot: Bobot buah dalam kg.
        keterangan: Objek KeteranganBuah, kondisi buah.
        tanggal_panen: Tanggal panen, teks YYYY-MM-DD.
        id_buah: Id buah. Dibuat otomatis (UUID) jika tidak diisi, dan tidak
            punya setter.
    """

    def __init__(self, pohon: Pohon, varietas: Varietas, bobot: float, keterangan: KeteranganBuah,
                 tanggal_panen: str, id_buah: Optional[str] = None):
        self.id_buah = id_buah or str(uuid.uuid4())
        self.pohon = pohon
        self.varietas = varietas
        self.bobot = bobot
        self.keterangan = keterangan
        self.tanggal_panen = tanggal_panen

    def get_id_buah(self):
        return self.id_buah

    def set_pohon(self, pohon: Pohon):
        self.pohon = pohon

    def get_pohon(self):
        return self.pohon

    def set_varietas(self, varietas: Varietas):
        self.varietas = varietas

    def get_varietas(self):
        return self.varietas

    def set_bobot(self, bobot: float):
        self.bobot = bobot

    def get_bobot(self):
        return self.bobot

    def set_keterangan(self, keterangan: KeteranganBuah):
        self.keterangan = keterangan

    def get_keterangan(self):
        return self.keterangan

    def set_tanggal_panen(self, tanggal_panen: str):
        self.tanggal_panen = tanggal_panen

    def get_tanggal_panen(self):
        return self.tanggal_panen


class PeriodePanen:
    """Satu periode panen, mis. "Raya 2026".

    Args:
        nama: Nama periode.
        tanggal_mulai: Tanggal mulai, teks YYYY-MM-DD.
        tanggal_selesai: Tanggal selesai, teks YYYY-MM-DD. None berarti periode
            masih berjalan.
        deskripsi: Keterangan tambahan, boleh kosong.
        id_periode: Id periode. Dibuat otomatis (UUID) jika tidak diisi, dan
            tidak punya setter.
    """

    def __init__(self, nama: str, tanggal_mulai: str, tanggal_selesai: Optional[str],
                 deskripsi: str = "", id_periode: Optional[str] = None):
        self.id_periode = id_periode or str(uuid.uuid4())
        self.nama = nama
        self.tanggal_mulai = tanggal_mulai
        self.tanggal_selesai = tanggal_selesai
        self.deskripsi = deskripsi

    def get_id_periode(self):
        return self.id_periode

    def set_nama(self, nama: str):
        self.nama = nama

    def get_nama(self):
        return self.nama

    def set_tanggal_mulai(self, tanggal_mulai: str):
        self.tanggal_mulai = tanggal_mulai

    def get_tanggal_mulai(self):
        return self.tanggal_mulai

    def set_tanggal_selesai(self, tanggal_selesai: Optional[str]):
        self.tanggal_selesai = tanggal_selesai

    def get_tanggal_selesai(self):
        return self.tanggal_selesai

    def set_deskripsi(self, deskripsi: str):
        self.deskripsi = deskripsi

    def get_deskripsi(self):
        return self.deskripsi

    def is_active(self):
        """Cek apakah periode masih berjalan.

        Returns:
            True jika tanggal selesai kosong, atau hari ini belum melewati
            tanggal selesai (hari tanggal selesai masih dihitung aktif).
        """
        if self.tanggal_selesai is None:
            return True
        else:
            today = datetime.now().date()
            tanggal_selesai_date = datetime.strptime(self.tanggal_selesai, "%Y-%m-%d").date()
            return today <= tanggal_selesai_date
