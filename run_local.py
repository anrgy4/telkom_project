"""Local launcher: install pinned dependencies once, then open the local UI."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener
import venv
import webbrowser

ROOT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8000"


def app_ready(url=URL):
    try:
        with build_opener(ProxyHandler({})).open(url + "/api/ready", timeout=2) as response:
            body = json.load(response)
        return isinstance(body, dict) and body.get("status") == "ok" and body.get("app") == "rantai-ivca"
    except (URLError, OSError, ValueError):
        return False


def prepare(root=ROOT):
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Gunakan Python 3.12 agar sesuai dengan paket yang sudah diuji.")
    runtime = root / ".runtime"
    runtime.mkdir(exist_ok=True)
    environment = root / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        print("Menyiapkan lingkungan aplikasi...", flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    lockfile = root / "requirements.lock"
    digest = hashlib.sha256(lockfile.read_bytes()).hexdigest()
    marker = runtime / "local-dependencies.sha256"
    if not marker.exists() or marker.read_text().strip() != digest:
        print("Memasang dependensi. Pertama kali memerlukan internet; tunggu sampai selesai.", flush=True)
        subprocess.run([str(python), "-m", "pip", "install", "-r", str(lockfile)], cwd=root, check=True)
        subprocess.run([str(python), "-m", "pip", "check"], cwd=root, check=True)
        marker.write_text(digest)
    browser_check = "from pathlib import Path; from playwright.sync_api import sync_playwright\nwith sync_playwright() as p: available=Path(p.chromium.executable_path).is_file()\nraise SystemExit(0 if available else 1)"
    configured_browser = os.getenv("CHROMIUM_PATH", "")
    if not (configured_browser and Path(configured_browser).is_file()):
        browser = subprocess.run([str(python), "-c", browser_check], cwd=root, stdout=subprocess.DEVNULL)
        if browser.returncode:
            print("Mengunduh Chromium untuk membaca halaman Google. Tunggu sampai selesai...", flush=True)
            subprocess.run([str(python), "-m", "playwright", "install", "chromium"], cwd=root, check=True)
    return python


def run():
    if app_ready():
        print("Aplikasi sudah aktif. Membuka browser...")
        webbrowser.open(URL)
        return
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", 8000)) == 0:
            raise RuntimeError("Port 8000 sedang dipakai aplikasi lain. Tutup aplikasi tersebut lalu coba lagi.")
    python = prepare()
    print("Menyalakan Rantai. Biarkan jendela ini terbuka selama aplikasi dipakai.", flush=True)
    process = subprocess.Popen([str(python), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=ROOT)
    try:
        for _ in range(40):
            if process.poll() is not None:
                raise RuntimeError("Aplikasi berhenti sebelum siap. Periksa pesan di jendela ini.")
            if app_ready():
                print("Aplikasi siap. Browser akan dibuka. Tekan Ctrl+C untuk menghentikan.", flush=True)
                webbrowser.open(URL)
                break
            time.sleep(.5)
        else:
            raise RuntimeError("Aplikasi belum siap setelah ditunggu. Tutup dan jalankan kembali.")
        process.wait()
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nAplikasi dihentikan.")
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print("\nBelum berhasil menjalankan aplikasi:", exc, file=sys.stderr)
        print("Lihat MULAI-DI-WINDOWS.md atau kirim pesan error yang terlihat (tanpa informasi rahasia).", file=sys.stderr)
        sys.exit(1)
