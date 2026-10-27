"""Windows-friendly local Ollama/model setup with no third-party API keys."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener

URL = "http://127.0.0.1:11434"
MODEL = "qwen2.5:3b"
opener = build_opener(ProxyHandler({}))


def tags():
    try:
        with opener.open(URL + "/api/tags", timeout=3) as response:
            return json.load(response).get("models", [])
    except (URLError, OSError, ValueError):
        return None


def main():
    models = tags()
    if models is None:
        binary = shutil.which("ollama")
        if not binary:
            binary = str(Path.home() / "AppData/Local/Programs/Ollama/ollama.exe")
            if not Path(binary).is_file():
                raise RuntimeError("Ollama belum ditemukan. Pasang dari https://ollama.com/download/windows, buka Ollama, lalu klik file ini lagi.")
        print("Menyalakan Ollama lokal...", flush=True)
        root = Path(__file__).resolve().parents[1]
        (root / ".runtime").mkdir(exist_ok=True)
        # Logs stay on the user's computer; never print keys or signed URLs.
        with (root / ".runtime/ollama-local.log").open("ab") as log:
            options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if sys.platform == "win32" else {"start_new_session": True}
            subprocess.Popen([binary, "serve"], stdout=log, stderr=log, **options)
        for _ in range(30):
            models = tags()
            if models is not None:
                break
            time.sleep(.5)
        else:
            raise RuntimeError("Ollama belum aktif. Buka aplikasi Ollama dari Start Menu, kemudian coba lagi.")
    if any(m.get("name") == MODEL for m in models):
        print("Model AI sudah tersedia. Buka Rantai dan klik 'Periksa kembali model' di Panduan.")
        return
    print("Mengunduh model AI sekitar 2 GB. Pertama kali saja; jangan tutup jendela ini.", flush=True)
    request = Request(URL + "/api/pull", data=json.dumps({"model": MODEL, "stream": True}).encode(), headers={"Content-Type": "application/json"})
    previous = ""
    with opener.open(request, timeout=600) as response:
        for line in response:
            if not line.strip():
                continue
            event = json.loads(line)
            if "error" in event:
                raise RuntimeError("Unduhan model gagal. Periksa internet/ruang disk lalu coba lagi. Ollama akan memakai kembali bagian unduhan yang masih valid.")
            status = event.get("status", "")
            if event.get("total"):
                percentage = int(event.get("completed", 0) / event["total"] * 100)
                status += f" ({percentage // 10 * 10}%)"
            if status != previous:
                print(status, flush=True)
                previous = status
    if not any(m.get("name") == MODEL for m in (tags() or [])):
        raise RuntimeError("Model belum tercatat selesai. Periksa Ollama lalu coba lagi.")
    print("Selesai. Model AI siap. Buka aplikasi Rantai lalu jalankan analisis.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nUnduhan dibatalkan. Jalankan file ini lagi untuk melanjutkan.")
        sys.exit(1)
    except (OSError, URLError, ValueError, RuntimeError) as exc:
        print("\nPenyiapan AI belum selesai:", exc, file=sys.stderr)
        sys.exit(1)
