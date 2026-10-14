# Buat folder dist\PencatatanKebun\ (berisi PencatatanKebun.exe) dengan PyInstaller.
# Jalankan dari folder proyek: powershell -ExecutionPolicy Bypass -File buat_exe.ps1
# Butuh .venv dengan requirements-dev.txt terpasang.
#
# Dipakai --onedir (satu folder), bukan --onefile: exe satu file yang membongkar
# dirinya ke folder sementara lebih sering dicurigai antivirus, dan lebih lambat dibuka.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Naikkan setiap kali exe baru dibagikan; tampil di Properties > Details exe.
$Versi = "1.0.0"

$angka = ($Versi.Split(".") + @("0", "0", "0"))[0..3] -join ", "
New-Item -ItemType Directory -Force build | Out-Null
$infoVersi = "build\versi.txt"
@"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($angka), prodvers=($angka)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('ProductName', 'Pencatatan Kebun'),
      StringStruct('FileDescription', 'Pencatatan Kebun'),
      StringStruct('CompanyName', 'Bryan Cornelius Lauwrence'),
      StringStruct('LegalCopyright', '(c) 2026 Bryan Cornelius Lauwrence'),
      StringStruct('OriginalFilename', 'PencatatanKebun.exe'),
      StringStruct('ProductVersion', '$Versi'),
      StringStruct('FileVersion', '$Versi')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"@ | Out-File -Encoding ascii $infoVersi

# Hapus hasil lama (termasuk exe --onefile versi sebelumnya).
if (Test-Path dist) { Remove-Item -Recurse -Force dist }

& .venv\Scripts\python -m PyInstaller `
    --noconfirm --clean `
    --onedir `
    --windowed `
    --name PencatatanKebun `
    --version-file $infoVersi `
    --paths src `
    --add-data "src\pencatatan_kebun\db\skema.sql;pencatatan_kebun\db" `
    src\pencatatan_kebun\__main__.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller gagal (kode $LASTEXITCODE)" }

Write-Host "Selesai: $PSScriptRoot\dist\PencatatanKebun\PencatatanKebun.exe (versi $Versi)"
