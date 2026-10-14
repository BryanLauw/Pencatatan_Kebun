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
- Library dari luar: hanya `openpyxl` (lihat `requirements.txt`); untuk membuat .exe
  juga PyInstaller (`requirements-dev.txt`).

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

Cadangan dari versi aplikasi lama bisa dipulihkan: skemanya diperbarui dulu (lihat
bagian berikut). Cadangan dari versi aplikasi yang lebih baru ditolak.

## Mengubah skema database

Setelah aplikasi dipakai dengan data asli, `kebun.db` pengguna **tidak boleh dihapus**.
Karena itu versi skema dicatat di dalam database (`PRAGMA user_version`), dan setiap
kali aplikasi dibuka, database lama diperbarui otomatis (`src/pencatatan_kebun/db/migrasi.py`):

- Database baru dibuat dari `skema.sql`, langsung versi terbaru.
- Database versi lama: sebelum diubah, disalin dulu ke
  `cadangan\sebelum-migrasi-v<versi>-<waktu>.db` (tidak ikut terhapus oleh batas 10
  cadangan otomatis). Lalu migrasi dijalankan satu per satu, masing-masing dalam satu
  transaksi dan dicek foreign key-nya; jika gagal, perubahan versi itu dibatalkan dan
  aplikasi menampilkan pesan tanpa membuka jendela.
- Database dari versi aplikasi yang lebih baru: ditolak dengan pesan, tidak diubah.

Database yang dibuat sebelum versi skema dicatat dianggap versi 1 (skema 14-10-2026).

Cara mengubah skema:

1. Ubah `skema.sql` (selalu skema lengkap terbaru). Kolom baru taruh di akhir tabel,
   sesuai hasil `ALTER TABLE ... ADD COLUMN`.
2. Naikkan `VERSI_SKEMA` di `db/migrasi.py`.
3. Tambahkan fungsi `MIGRASI[<versi baru>]` yang mengubah database versi sebelumnya,
   mis. `conn.execute("ALTER TABLE pohon ADD COLUMN catatan TEXT")`. Jangan pakai
   `executescript` dan jangan commit sendiri. Untuk mengubah CHECK atau tipe kolom,
   buat ulang tabelnya (buat tabel baru, salin data, hapus tabel lama, ganti nama).
4. Jalankan tes. `tests/test_migrasi.py` membuat database dari `tests/acuan/skema_v1.sql`
   (salinan beku versi 1, jangan diubah), menjalankan semua migrasi, lalu
   membandingkan kolom, foreign key, index, dan trigger dengan database baru dari
   `skema.sql`; tes gagal jika ada perubahan skema tanpa migrasi. CHECK tidak ikut
   dibandingkan, jadi perubahan CHECK perlu diuji sendiri.

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
  db/                   koneksi SQLite, skema.sql (aturan data: CHECK, UNIQUE,
                        foreign key, trigger periode), dan migrasi.py (versi skema)
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

## Membuat .exe

Supaya aplikasi bisa dipakai di komputer tanpa Python, dibuat folder berisi
`PencatatanKebun.exe` dengan [PyInstaller](https://pyinstaller.org/):

```powershell
.venv\Scripts\python -m pip install -r requirements-dev.txt   # sekali saja
powershell -ExecutionPolicy Bypass -File buat_exe.ps1
```

Hasilnya folder `dist\PencatatanKebun\` (sekitar 29 MB): `PencatatanKebun.exe` dan
folder `_internal\` berisi Python, tkinter, openpyxl, dan `skema.sql`. Exe tidak bisa
dijalankan tanpa `_internal\` di sebelahnya. Folder `build\` dan `dist\` tidak masuk git.

Nomor versi ada di `$Versi` di bagian atas `buat_exe.ps1`; naikkan setiap kali exe baru
dibagikan. Versi, nama produk, dan pembuat tampil di klik kanan exe -> **Properties ->
Details**.

Dipakai satu folder (`--onedir`), bukan satu file (`--onefile`): exe satu file membongkar
dirinya ke folder sementara setiap dibuka, sehingga lebih lambat dan lebih sering
dicurigai antivirus.

### Memasang di komputer pemilik kebun

1. Salin seluruh folder `dist\PencatatanKebun\` lewat **flashdisk**, mis. ke
   `C:\PencatatanKebun\`. Hindari mengirim lewat unduhan (browser, email, WhatsApp,
   Google Drive): file unduhan ditandai "dari internet" sehingga diperiksa SmartScreen.
2. Klik kanan `PencatatanKebun.exe` -> **Kirim ke -> Desktop (buat pintasan)**.
3. Data tetap di `%APPDATA%\PencatatanKebun\`, terpisah dari exe. Mengganti folder
   aplikasi dengan versi baru tidak menghapus data.

### Jika Windows memblokir exe

Exe tidak bertanda tangan digital, jadi Windows bisa mencurigainya:

- **SmartScreen** ("Windows melindungi PC Anda"): pilih **Info selengkapnya -> Tetap
  jalankan**. Atau sebelum dibuka: klik kanan exe -> Properties -> centang **Unblock**.
- **Antivirus / Windows Defender** menganggap exe berbahaya: laporkan sebagai salah
  deteksi di <https://www.microsoft.com/en-us/wdsi/filesubmission>, atau tambahkan folder
  aplikasi ke Windows Security -> Virus & threat protection -> Exclusions.
- **Smart App Control** ("An Application Control policy has blocked this file", atau
  pesan bahwa Smart App Control memblokir aplikasi): fitur Windows 11 yang memblokir
  aplikasi tak bertanda tangan yang belum dikenal Microsoft. Keputusannya dari layanan
  cloud Microsoft per file dan tidak menentu: saat diuji, exe yang sama kadang diblokir
  lalu dibolehkan, dan setiap build baru bisa diblokir lagi. Smart App Control tidak punya
  pengecualian per aplikasi. Pilihannya: matikan Smart App Control (Windows Security ->
  App & browser control -> Smart App Control), atau tanda tangani exe dengan sertifikat
  code signing yang dipercaya Windows (berbayar). Cek dulu di komputer pemilik kebun;
  Smart App Control hanya aktif di sebagian komputer Windows 11.

Exe hanya berjalan di Windows 64-bit (sama dengan Python yang dipakai untuk build).

## Rencana berikutnya

- Uji manual menyeluruh, lalu commit dan beri tag versi (mis. `v1.0.0`) sebelum exe
  dikirim ke pemilik kebun.
- Panduan singkat untuk pemilik kebun (opsional).
