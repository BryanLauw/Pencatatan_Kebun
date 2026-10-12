from typing import Optional


class ServiceException(Exception):
    """Induk semua kesalahan service. Pesannya boleh langsung ditampilkan ke pengguna.

    ui cukup menangkap exception ini dan menampilkan e.pesan. Exception lain
    (bukan turunan kelas ini) berarti bug dan pesannya tidak perlu ditampilkan.

    Args:
        pesan: Kalimat untuk pengguna. Jika None, dipakai pesan_bawaan.
        kolom: Nama isian form yang bermasalah (mis. "bobot"), agar ui bisa
            menyorotnya. None jika tidak terkait satu isian tertentu.

    Attributes:
        pesan_bawaan: Pesan yang dipakai jika pesan tidak diisi. Timpa di turunan.
        pesan: Kalimat untuk pengguna. Selalu tersedia di setiap turunan.
        kolom: Nama isian form yang bermasalah, atau None. Selalu tersedia di
            setiap turunan.

    Note:
        Cara membuat turunan:

        - Pesannya selalu sama: cukup timpa pesan_bawaan.
        - Pesannya butuh data: tulis __init__ sendiri yang menyusun pesan, lalu
          panggil super().__init__(pesan, kolom=...). Contoh: NamaKosongException
          menerima label lalu menyusun "<label> wajib diisi!".
        - Kelas pengelompok (mis. InputTidakValidException): jangan tulis __init__
          dengan parameter berbeda, karena semua turunannya memanggil super().__init__
          dengan parameter pesan dan kolom.
    """

    pesan_bawaan = "Terjadi kesalahan"

    def __init__(self, pesan: Optional[str] = None, kolom: Optional[str] = None):
        self.pesan = pesan or self.pesan_bawaan
        self.kolom = kolom
        super().__init__(self.pesan)


# ---- input dari pengguna tidak valid ----

class InputTidakValidException(ServiceException):
    """Induk semua kesalahan isian form yang tidak memenuhi aturan.

    Kelas pengelompok: ui bisa menangkap semua kesalahan isian sekaligus dengan
    `except InputTidakValidException`, terpisah dari kesalahan data di database.
    Boleh juga dilempar langsung sebagai cadangan untuk isian salah yang tidak
    punya kelas sendiri.
    """

    pesan_bawaan = "Input tidak valid"


class BobotTidakValidException(InputTidakValidException):
    """Bobot buah kosong, bukan angka, atau tidak lebih dari 0.

    Pesannya selalu sama dan tidak memuat nilai bobot, karena pengguna sudah
    melihat isiannya di form. Pemeriksaan nilainya dilakukan di service.
    """

    def __init__(self):
        super().__init__(pesan="Bobot tidak valid! Bobot harus lebih dari 0", kolom="bobot")


class TanggalTidakValidException(InputTidakValidException):
    """Tanggal salah format, tidak ada di kalender (mis. 2026-02-30),
    di masa depan, atau tanggal selesai tidak setelah tanggal mulai.

    Args:
        alasan: Kenapa tanggal ditolak, mis. "Format harus YYYY-MM-DD" atau
            "Tidak boleh di masa depan". Ditambahkan di belakang pesan.
        kolom: Isian tanggal yang salah: "tanggal_panen" (bawaan),
            "tanggal_mulai", atau "tanggal_selesai".
    """

    def __init__(self, alasan: str, kolom: str = "tanggal_panen"):
        super().__init__(f"Tanggal tidak valid! {alasan}", kolom=kolom)


class NamaKosongException(InputTidakValidException):
    """Nama wajib diisi tetapi kosong atau hanya spasi
    (nama jenis, varietas, keterangan, atau periode).

    Args:
        label: Nama isian untuk pesan, mis. "Nama varietas"
            (menjadi "Nama varietas wajib diisi!").
        kolom: Nama isian untuk ui, mis. "nama_varietas".
    """

    def __init__(self, label: str, kolom: str):
        super().__init__(f"{label} wajib diisi!", kolom=kolom)


class NomorPohonTidakValidException(InputTidakValidException):
    """Nomor pohon bukan bilangan bulat positif.

    Pesannya selalu sama. Pemeriksaan nilainya dilakukan di service.
    """

    def __init__(self):
        super().__init__(
            pesan="Nomor pohon tidak valid! Nomor pohon harus bilangan bulat positif",
            kolom="nomor_pohon",
        )


class JumlahBuahTidakValidException(InputTidakValidException):
    """Jumlah buah di stok pohon bukan bilangan bulat 0 atau lebih, atau lebih
    sedikit dari buah yang sudah tercatat di periode itu.

    Args:
        alasan: Kenapa jumlah ditolak. Ditambahkan di belakang pesan.
    """

    def __init__(self, alasan: str = "Jumlah buah harus bilangan bulat 0 atau lebih"):
        super().__init__(f"Jumlah buah tidak valid! {alasan}", kolom="jumlah_buah")


# ---- masalah dengan data di database ----

class DataTidakDitemukanException(ServiceException):
    """Data yang dirujuk tidak ada, mis. id salah atau sudah dihapus di menu lain.

    Dipakai juga saat create/update ditolak foreign key (sqlite3.IntegrityError
    "FOREIGN KEY constraint failed").

    Args:
        nama_data: Data yang dicari, mis. "pohon" atau "varietas Musang King".
        kolom: Isian terkait di form, jika ada.
    """

    def __init__(self, nama_data: str, kolom: Optional[str] = None):
        super().__init__(f"Data {nama_data} tidak ditemukan!", kolom=kolom)


class DataSudahAdaException(ServiceException):
    """Melanggar aturan unik, mis. nama jenis atau nama keterangan sudah
    dipakai, nama varietas sudah ada di jenis yang sama, atau nomor pohon sudah
    ada di varietas yang sama
    (sqlite3.IntegrityError "UNIQUE constraint failed").

    Args:
        nama_data: Data yang bentrok, mis. "nomor pohon 7".
        kolom: Isian terkait di form, mis. "nomor_pohon".
    """

    def __init__(self, nama_data: str, kolom: Optional[str] = None):
        super().__init__(f"Data {nama_data} sudah ada!", kolom=kolom)


class DataMasihDipakaiException(ServiceException):
    """Tidak bisa dihapus karena masih dipakai data lain, mis. pohon yang sudah
    punya catatan buah atau stok, varietas yang masih punya pohon, jenis yang
    masih punya varietas, atau periode yang sudah punya stok pohon
    (delete ditolak foreign key, sqlite3.IntegrityError "FOREIGN KEY constraint failed").

    Args:
        nama_data: Data yang akan dihapus, mis. "varietas Musang King".
        kolom: Isian terkait di form, jika ada.
    """

    def __init__(self, nama_data: str, kolom: Optional[str] = None):
        super().__init__(f"Data {nama_data} masih dipakai!", kolom=kolom)


class PeriodeBertumpukException(ServiceException):
    """Periode panen tumpang tindih dengan periode lain
    (ditolak trigger di skema dengan pesan 'Periode panen tumpang tindih ...').

    Args:
        nama_periode: Periode yang sedang dibuat atau diubah.
        nama_periode_lain: Periode yang bertabrakan, jika diketahui. Pesan dari
            trigger tidak menyebutkannya; jika None, pesan memakai "periode panen lain".
        kolom: Isian terkait di form, mis. "tanggal_mulai".
    """

    def __init__(self, nama_periode: str, nama_periode_lain: Optional[str] = None, kolom: Optional[str] = None):
        lain = " dengan periode panen" + (f" {nama_periode_lain}" if nama_periode_lain else " lain")
        super().__init__(f"Periode panen {nama_periode} bertumpuk{lain}!", kolom=kolom)


class PeriodeSudahDitutupException(ServiceException):
    """Periode yang diminta untuk ditutup sudah punya tanggal selesai.

    Args:
        nama_periode: Periode yang akan ditutup.
    """

    def __init__(self, nama_periode: str):
        super().__init__(f"Periode panen {nama_periode} sudah ditutup!", kolom="periode_panen")
