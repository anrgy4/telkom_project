"""Create a source-only Windows ZIP, excluding cloud environments and secrets."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root=Path(__file__).resolve().parents[1]
files=[root/n for n in ["1-JALANKAN-APLIKASI.bat","2-SIAPKAN-AI-SEKALI.bat","run_local.py","MULAI-DI-WINDOWS.md","README.md",".gitignore","requirements.txt","requirements.lock","scripts/setup-local-ai.py"]]
for directory,extensions in [("app",{".py",".js",".html",".css",".json"}),("docs",{".md"}),("tests",{".py"}),("outputs",{".html",".svg",".pdf",".md"})]:
    files.extend(p for p in (root/directory).rglob("*") if p.is_file() and p.suffix in extensions and "__pycache__" not in p.parts)
archive=root/"outputs/Rantai-Windows.zip"
with ZipFile(archive,"w",ZIP_DEFLATED) as z:
    for path in sorted(set(files)):
        name="Rantai-Windows/"+path.relative_to(root).as_posix()
        data=path.read_bytes()
        if path.suffix==".bat":
            data=data.replace(b"\r\n",b"\n").replace(b"\n",b"\r\n")
        z.writestr(name,data)
with ZipFile(archive) as z:
    assert z.testzip() is None
    assert all(not any(part in {".git",".venv",".runtime",".cache",".env","__pycache__"} for part in Path(name).parts) for name in z.namelist())
    assert all(not name.endswith(".zip") for name in z.namelist())
    assert "Rantai-Windows/1-JALANKAN-APLIKASI.bat" in z.namelist()
    assert "Rantai-Windows/scripts/setup-local-ai.py" in z.namelist()
    print(f"Verified {archive.name}: {len(z.namelist())} files, {archive.stat().st_size:,} bytes; no venv, runtime, cache, Git metadata, or .env files.")
