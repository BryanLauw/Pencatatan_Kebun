# Pencatatan Kebun

Aplikasi desktop Windows untuk mencatat panen kebun buah (mis. durian dan alpukat),
pengganti catatan Excel per jenis yang selama ini dipakai pemilik kebun. Dibuat dengan
Python, tkinter, dan SQLite, dengan bahasa Indonesia dan huruf besar supaya mudah
dipakai orang yang tidak terbiasa dengan komputer.

## Fitur

Aplikasi dibuka dalam satu jendela dengan lima tab:

| Tab | Kegunaan |
|---|---|
| **Dashboard** | Ringkasan satu periode per jenis: kartu stok/panen/sisa/kg, pie panen per varietas dan per keterangan, tabel varietas yang bisa dibuka per keterangan. Tombol **Ekspor ke Excel**. |
| **Catat Panen** | Catat satu buah per simpan (pohon, keterangan, bobot) pada tanggal terpilih. Memberi peringatan jika sisa buah pohon sudah habis, pohon belum punya stok, atau tanggal di luar periode. |
| **Stok Pohon** | Jumlah buah di tiap pohon per periode, beserta jumlah tercatat dan sisanya. Isian cepat: ketik jumlah, Enter, lanjut ke pohon berikutnya. |
| **Periode Panen** | Buka, ubah, tutup, dan hapus periode. Membuka periode baru otomatis menutup periode yang masih aktif. |
| **Data Master** | Jenis tanaman, varietas, pohon, dan keterangan buah (mis. Baik, Gugur, Rusak). Data lain hanya dipilih dari dropdown, jadi nama selalu seragam. |

Ekspor Excel menghasilkan satu file per periode: sheet **Ringkasan**, satu sheet per
jenis (format seperti Excel lama, satu baris per pohon dan satu kolom per tanggal
panen, ditambah ringkasan per varietas dan keterangan), dan sheet **Catatan buah**
(setiap buah dengan bobotnya). Hasil hitungan berupa rumus Excel, jadi ikut berubah
jika angka dasarnya diubah.

## Persyaratan

- Windows 10/11.
- Python 3.13 atau lebih baru dari [python.org](https://www.python.org/), dengan pilihan
  **"tcl/tk and IDLE"** tercentang saat instalasi (untuk tkinter).
- Library dari luar: hanya `openpyxl` (lihat `requirements.txt`).

## Menyiapkan

Dari folder proyek, di PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Jika PowerShell menolak menjalankan `Activate.ps1`, jalankan sekali
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, atau pakai langsung
`.venv\Scripts\python` seperti contoh di bawah.

## Menjalankan aplikasi

```powershell
cd src
..\.venv\Scripts\python -m pencatatan_kebun
```

Database dibuat otomatis saat pertama kali dijalankan. Urutan pengisian untuk
pertama kali: **Data Master** (jenis, varietas, pohon, keterangan) -> **Periode Panen**
(buka periode) -> **Stok Pohon** -> **Catat Panen** -> lihat hasilnya di **Dashboard**.

## Lokasi data

| File | Lokasi |
|---|---|
| Database | `%APPDATA%\PencatatanKebun\kebun.db` (mis. `C:\Users\<nama>\AppData\Roaming\PencatatanKebun\kebun.db`) |
| Log error | `kebun.log` di folder yang sama |
| Cadangan otomatis | folder `cadangan\` di folder yang sama, 10 terakhir (`kebun-YYYYMMDD-HHMMSS.db`) |

## Cadangan data

Semua catatan ada di satu file `kebun.db`, jadi aplikasi menyediakan menu **Cadangan**:

- **Simpan cadangan...**: salin semua data ke file pilihan (mis. di flashdisk), nama
  bawaan `Cadangan Kebun DD-MM-YYYY.db`.
- **Pulihkan dari cadangan...**: ganti semua data dengan isi file cadangan, setelah
  konfirmasi. File dicek dulu (harus database Pencatatan Kebun yang utuh); data
  sebelum dipulihkan otomatis dicadangkan, jadi pemulihan yang keliru bisa dibatalkan.
- **Arsipkan dan kosongkan data panen...**: simpan semua data ke file arsip (nama
  bawaan `Arsip Kebun DD-MM-YYYY.db`), lalu hapus semua periode, stok, dan catatan
  buah; data master (jenis, varietas, pohon, keterangan) tetap. Data baru dihapus
  setelah arsip berhasil ditulis dan dicek, dan dibuat juga cadangan otomatis. Data
  lama bisa dilihat lagi dengan memulihkan file arsip.
- **Buka folder cadangan otomatis**: setiap kali aplikasi ditutup, dibuat cadangan
  otomatis; hanya 10 terbaru yang disimpan.

Cadangan dibuat dengan API backup SQLite (`src/pencatatan_kebun/cadangan.py`), aman
walau database sedang terbuka.

Selama tahap pengembangan belum ada migrasi database: jika `src/pencatatan_kebun/db/skema.sql`
diubah, hapus `kebun.db` lama agar dibuat ulang dengan skema baru.

## Tes

```powershell
.venv\Scripts\python -m unittest discover -s tests
```

- Jalankan dengan Python dari `.venv`, karena `openpyxl` hanya terpasang di sana.
- Opsi `-s tests` wajib; tanpa itu tidak ada tes yang ditemukan.
- Tes database memakai SQLite `:memory:`, jadi database asli tidak tersentuh.
- Satu tes ekspor menghitung ulang rumus Excel dengan LibreOffice
  (`C:\Program Files\LibreOffice\program\soffice.exe`); tes itu dilewati jika
  LibreOffice tidak terpasang.

Pemeriksaan gaya kode memakai [Ruff](https://docs.astral.sh/ruff/) (mis. lewat
ekstensi Ruff di VS Code) dengan aturan bawaan.

## Struktur kode

```
src/pencatatan_kebun/
  __main__.py, app.py   titik masuk: buka database, buat service, buka jendela
  config.py             lokasi database dan format tanggal tampilan
  models.py             kelas data: JenisTanaman, Varietas, Pohon, KeteranganBuah,
                        Buah, PeriodePanen, StokPohon
  db/                   koneksi SQLite dan skema.sql (aturan data: CHECK, UNIQUE,
                        foreign key, trigger periode)
  repo/                 baca/tulis tabel (create/read/update/delete)
  services/             aturan bisnis dan validasi; melempar ServiceException
                        berisi pesan untuk pengguna
  ekspor/excel.py       ekspor laporan periode ke .xlsx
  cadangan.py           cadangan manual/otomatis dan pemulihan database
  ui/                   tkinter: jendela_utama.py, satu layar_*.py per tab, komponen
                        bersama (komponen.py, kalender.py, diagram.py, format.py)
tests/                  unittest per lapisan
docs/rencana-ui.md      rencana dan keputusan desain UI
ref/                    contoh Excel lama dari pemilik kebun
```

Alur data: **ui -> services -> repo -> SQLite**. Layar tidak mengakses database
langsung; service menerima objek model (dipilih dari dropdown), bukan nama.

## Rencana berikutnya

- Paket `.exe` (PyInstaller) supaya bisa dijalankan tanpa memasang Python.
- Migrasi skema database, begitu aplikasi dipakai dengan data asli.
