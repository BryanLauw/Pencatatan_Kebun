# Buat folder dist\PencatatanKebun\ (exe + panduan PDF) dan zip-nya untuk dikirim.
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

# Panduan pemakai: docs\panduan\panduan.html -> PDF di samping exe, dicetak oleh
# Microsoft Edge (bawaan Windows). Gambarnya dibuat ulang dengan ambil_gambar.py.
$edge = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
          "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe") |
        Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $edge) { throw "Microsoft Edge tidak ditemukan; dibutuhkan untuk membuat PDF panduan" }
$pdf = "$PSScriptRoot\dist\PencatatanKebun\Panduan Pencatatan Kebun.pdf"
$html = ([Uri]"$PSScriptRoot\docs\panduan\panduan.html").AbsoluteUri
$profil = "$PSScriptRoot\build\edge"
# Edge menulis pesan biasa ke stderr; jangan dianggap error (hasilnya dicek lewat file PDF).
$ErrorActionPreference = "Continue"
& $edge --headless --disable-gpu --no-pdf-header-footer "--user-data-dir=$profil" `
    "--print-to-pdf=$pdf" $html 2>&1 | Out-Null
$ErrorActionPreference = "Stop"
if (-not (Test-Path $pdf)) { throw "PDF panduan gagal dibuat" }

# Zip untuk dikirim: folder PencatatanKebun (exe, _internal, panduan).
$zip = "$PSScriptRoot\dist\PencatatanKebun-$Versi.zip"
Compress-Archive -Path "$PSScriptRoot\dist\PencatatanKebun" -DestinationPath $zip -Force

Write-Host "Selesai (versi $Versi):"
Write-Host "  $PSScriptRoot\dist\PencatatanKebun\PencatatanKebun.exe"
Write-Host "  $pdf"
Write-Host "  $zip"
