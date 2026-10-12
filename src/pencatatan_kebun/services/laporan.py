import sqlite3
from datetime import date

from pencatatan_kebun.models import JenisTanaman, PeriodePanen
from pencatatan_kebun.repo.buah import RepoBuah
from pencatatan_kebun.repo.jenis_tanaman import RepoJenisTanaman
from pencatatan_kebun.repo.periode_panen import RepoPeriodePanen
from pencatatan_kebun.repo.stok_pohon import RepoStokPohon
from pencatatan_kebun.repo.varietas import RepoVarietas
from pencatatan_kebun.services.exception import DataTidakDitemukanException


def _rata(total: float, jumlah: int) -> float:
    return total / jumlah if jumlah else 0.0


def _persen(bagian: int, jumlah: int) -> float:
    return bagian / jumlah * 100 if jumlah else 0.0


class LaporanService:
    """Ringkasan hasil panen satu periode untuk dashboard, dipisah per jenis.

    Semua fungsi hanya membaca data. Bobot dalam kg. Aturan angka:

    - Buah dihitung jika tanggal_panen di dalam rentang periode (batas ikut).
      Periode yang masih aktif dihitung sampai hari ini.
    - Semua keterangan dihitung panen, termasuk buah gugur.
    - sisa = jumlah_stok - jumlah_panen. Bisa negatif jika ada panen dari
      pohon yang belum punya stok di periode itu.
    - Persentase keterangan di tiap varietas dihitung dari panen varietas itu
      (mis. "92% Bawor baik"); di ringkasan jenis dihitung dari panen seluruh
      jenis (mis. "91% Durian baik").
    - Rata-rata dan persentase bernilai 0 jika belum ada buah.
    - Angka tidak dibulatkan; pembulatan diatur di ui.

    Service selalu memberi semua keterangan; ui yang memilih mana yang
    ditampilkan (mis. rincian keterangan baru muncul saat varietas dibuka).

    Args:
        conn: Koneksi database dari buka_koneksi.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.repo_buah = RepoBuah(conn)
        self.repo_periode = RepoPeriodePanen(conn)
        self.repo_stok = RepoStokPohon(conn)
        self.repo_jenis = RepoJenisTanaman(conn)
        self.repo_varietas = RepoVarietas(conn)

    def _rentang(self, id_periode: str) -> tuple[PeriodePanen, str, str]:
        """Ambil periode beserta rentang tanggal yang dihitung.

        Args:
            id_periode: Id periode panen.

        Returns:
            (periode, mulai, selesai), tanggal format YYYY-MM-DD. Jika periode
            masih aktif, selesai = hari ini.

        Raises:
            DataTidakDitemukanException: Periode tidak ditemukan.
        """
        periode = self.repo_periode.read(id_periode)
        if periode is None:
            raise DataTidakDitemukanException("periode panen", kolom="id_periode")
        selesai = periode.get_tanggal_selesai() or date.today().isoformat()
        return periode, periode.get_tanggal_mulai(), selesai

    def _cek_jenis(self, jenis: JenisTanaman) -> None:
        """Cek jenis masih ada di database.

        Raises:
            DataTidakDitemukanException: Jenis tidak ditemukan.
        """
        if self.repo_jenis.read(jenis.get_id_jenis()) is None:
            raise DataTidakDitemukanException("jenis tanaman", kolom="id_jenis")

    def ringkasan_jenis(self, id_periode: str, jenis: JenisTanaman) -> dict:
        """Ringkasan satu jenis dalam satu periode: total jenis, lalu per
        varietas (seperti baris ringkasan di bawah Excel), dan di dalam tiap
        varietas rincian per keterangan.

        Args:
            id_periode: Id periode panen.
            jenis: Jenis tanaman yang dilaporkan, mis. Durian.

        Returns:
            {
              "ringkasan": {
                "jumlah_stok": int, "jumlah_panen": int, "sisa": int,
                "total_bobot": float, "rata_rata_bobot": float,
                "per_keterangan": {
                  nama_keterangan: {"jumlah_buah": int, "persentase": float,
                                    "total_bobot": float},
                },
              },
              "per_varietas": {
                nama_varietas: {
                  "varietas": Varietas,
                  "jumlah_stok": int, "jumlah_panen": int, "sisa": int,
                  "total_bobot": float, "rata_rata_bobot": float,
                  "bobot_min": float | None, "bobot_max": float | None,
                  "per_keterangan": {...sama seperti di ringkasan...},
                },
              },
            }

            - "per_varietas" berisi varietas yang punya stok atau panen di
              periode itu, urut berdasarkan nama varietas.
            - bobot_min/bobot_max None jika varietas belum ada panen.
            - Semua "per_keterangan" berisi keterangan yang dipakai jenis ini
              di periode itu, dengan kunci dan urutan sama (urut nama);
              kombinasi tanpa buah bernilai 0. Jadi ui bisa langsung
              menyusunnya sebagai tabel varietas x keterangan.

        Raises:
            DataTidakDitemukanException: Periode atau jenis tidak ditemukan.
        """
        _, mulai, selesai = self._rentang(id_periode)
        self._cek_jenis(jenis)

        baris_buah = self.repo_buah.summarize_by_varietas_keterangan(jenis.get_id_jenis(), mulai, selesai)
        baris_stok = self.repo_stok.sum_by_varietas(id_periode, jenis.get_id_jenis())
        daftar_keterangan = sorted({b["nama_keterangan"] for b in baris_buah}, key=str.casefold)

        def keterangan_kosong() -> dict:
            return {nama: {"jumlah_buah": 0, "persentase": 0.0, "total_bobot": 0.0}
                    for nama in daftar_keterangan}

        def ambil_varietas(id_varietas: str) -> dict:
            if id_varietas not in data:
                data[id_varietas] = {
                    "varietas": self.repo_varietas.read(id_varietas),
                    "jumlah_stok": 0, "jumlah_panen": 0, "sisa": 0,
                    "total_bobot": 0.0, "rata_rata_bobot": 0.0,
                    "bobot_min": None, "bobot_max": None,
                    "per_keterangan": keterangan_kosong(),
                }
            return data[id_varietas]

        data = {}
        for baris in baris_stok:
            ambil_varietas(baris["id_varietas"])["jumlah_stok"] = baris["jumlah_stok"]
        for baris in baris_buah:
            v = ambil_varietas(baris["id_varietas"])
            v["jumlah_panen"] += baris["jumlah_buah"]
            v["total_bobot"] += baris["total_bobot"]
            v["bobot_min"] = baris["bobot_min"] if v["bobot_min"] is None else min(v["bobot_min"], baris["bobot_min"])
            v["bobot_max"] = baris["bobot_max"] if v["bobot_max"] is None else max(v["bobot_max"], baris["bobot_max"])
            k = v["per_keterangan"][baris["nama_keterangan"]]
            k["jumlah_buah"] = baris["jumlah_buah"]
            k["total_bobot"] = baris["total_bobot"]

        ringkasan = {
            "jumlah_stok": 0, "jumlah_panen": 0, "sisa": 0,
            "total_bobot": 0.0, "rata_rata_bobot": 0.0,
            "per_keterangan": keterangan_kosong(),
        }
        for v in data.values():
            v["sisa"] = v["jumlah_stok"] - v["jumlah_panen"]
            v["rata_rata_bobot"] = _rata(v["total_bobot"], v["jumlah_panen"])
            for nama, k in v["per_keterangan"].items():
                k["persentase"] = _persen(k["jumlah_buah"], v["jumlah_panen"])
                total = ringkasan["per_keterangan"][nama]
                total["jumlah_buah"] += k["jumlah_buah"]
                total["total_bobot"] += k["total_bobot"]
            ringkasan["jumlah_stok"] += v["jumlah_stok"]
            ringkasan["jumlah_panen"] += v["jumlah_panen"]
            ringkasan["total_bobot"] += v["total_bobot"]

        ringkasan["sisa"] = ringkasan["jumlah_stok"] - ringkasan["jumlah_panen"]
        ringkasan["rata_rata_bobot"] = _rata(ringkasan["total_bobot"], ringkasan["jumlah_panen"])
        for k in ringkasan["per_keterangan"].values():
            k["persentase"] = _persen(k["jumlah_buah"], ringkasan["jumlah_panen"])

        urut = sorted(data.values(), key=lambda v: v["varietas"].get_nama_varietas().casefold())
        return {
            "ringkasan": ringkasan,
            "per_varietas": {v["varietas"].get_nama_varietas(): v for v in urut},
        }

    def ringkasan_per_pohon(self, id_periode: str, jenis: JenisTanaman) -> list[dict]:
        """Ringkasan per pohon satu jenis dalam satu periode, untuk tabel seperti
        Excel lama (dipakai ekspor Excel nanti).

        Args:
            id_periode: Id periode panen.
            jenis: Jenis tanaman yang dilaporkan.

        Returns:
            Satu dict per pohon yang punya stok atau panen di periode itu:
            {"nama_varietas": str, "nomor_pohon": int, "jumlah_stok": int,
            "jumlah_panen": int, "sisa": int, "total_bobot": float},
            urut berdasarkan nama varietas lalu nomor pohon. jumlah_stok 0 jika
            pohon belum punya stok.

        Raises:
            DataTidakDitemukanException: Periode atau jenis tidak ditemukan.
        """
        _, mulai, selesai = self._rentang(id_periode)
        self._cek_jenis(jenis)

        data = {}
        for baris in self.repo_stok.sum_by_pohon(id_periode, jenis.get_id_jenis()):
            data[baris["id_pohon"]] = {
                "nama_varietas": baris["nama_varietas"], "nomor_pohon": baris["nomor_pohon"],
                "jumlah_stok": baris["jumlah_stok"], "jumlah_panen": 0, "total_bobot": 0.0,
            }
        for baris in self.repo_buah.summarize_by_pohon(jenis.get_id_jenis(), mulai, selesai):
            pohon = data.setdefault(baris["id_pohon"], {
                "nama_varietas": baris["nama_varietas"], "nomor_pohon": baris["nomor_pohon"],
                "jumlah_stok": 0,
            })
            pohon["jumlah_panen"] = baris["jumlah_buah"]
            pohon["total_bobot"] = baris["total_bobot"]

        hasil = sorted(data.values(), key=lambda p: (p["nama_varietas"].casefold(), p["nomor_pohon"]))
        for pohon in hasil:
            pohon["sisa"] = pohon["jumlah_stok"] - pohon["jumlah_panen"]
        return hasil

    def dashboard(self, id_periode: str) -> dict:
        """Semua data dashboard satu periode dalam satu panggilan.

        ui cukup memanggil PeriodeService.periode_aktif(), lalu dashboard()
        dengan id periode itu.

        Args:
            id_periode: Id periode panen.

        Returns:
            {"periode": PeriodePanen,
             "per_jenis": {nama_jenis: {"jenis": JenisTanaman,
                                        "ringkasan": ...,
                                        "per_varietas": ...}}}.
            "ringkasan" dan "per_varietas" sama dengan hasil ringkasan_jenis.
            Hanya jenis yang punya stok atau panen di periode itu, urut
            berdasarkan nama jenis (satu tab per jenis di ui).

        Raises:
            DataTidakDitemukanException: Periode tidak ditemukan.
        """
        periode, _, _ = self._rentang(id_periode)

        per_jenis = {}
        for jenis in self.repo_jenis.read_all():
            ringkasan = self.ringkasan_jenis(id_periode, jenis)
            if ringkasan["per_varietas"]:
                per_jenis[jenis.get_nama_jenis()] = {"jenis": jenis, **ringkasan}
        return {"periode": periode, "per_jenis": per_jenis}
