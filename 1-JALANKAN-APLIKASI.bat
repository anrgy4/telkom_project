@echo off
setlocal
cd /d "%~dp0"
title Rantai - Jalankan Aplikasi
py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    py -3.12 run_local.py
    if errorlevel 1 goto failed
    exit /b 0
)
python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)" >nul 2>&1
if not errorlevel 1 (
    python run_local.py
    if errorlevel 1 goto failed
    exit /b 0
)
echo Python 3.12 belum ditemukan.
echo Pasang Python 3.12 dari https://www.python.org/downloads/release/python-31210/
echo Saat memasang, centang Add python.exe to PATH.
echo Setelah selesai, klik file ini lagi.
:failed
echo.
echo Aplikasi belum berhasil dijalankan. Baca pesan di atas.
pause
exit /b 1
