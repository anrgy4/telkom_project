@echo off
setlocal
cd /d "%~dp0"
title Rantai - Siapkan AI Lokal
echo Jalankan file ini sekali untuk menyiapkan model AI sekitar 2 GB.
echo Pastikan Ollama sudah dipasang dari https://ollama.com/download/windows
echo.
py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    py -3.12 scripts\setup-local-ai.py
    if errorlevel 1 goto failed
    goto done
)
python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)" >nul 2>&1
if not errorlevel 1 (
    python scripts\setup-local-ai.py
    if errorlevel 1 goto failed
    goto done
)
echo Python 3.12 belum ditemukan. Pasang dulu lalu buka file ini lagi.
goto failed
:done
echo.
echo Selesai. Kembali ke browser Rantai untuk mencoba analisis.
pause
exit /b 0
:failed
echo.
echo AI belum siap. Baca pesan di atas lalu coba lagi.
pause
exit /b 1
