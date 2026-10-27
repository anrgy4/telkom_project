"""Optional CLI; the same operation is available in the Katalog resmi UI tab."""
import asyncio
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.catalog import refresh_catalog

data=asyncio.run(refresh_catalog())
print("Status katalog:",data["status"],"| Produk/halaman solusi terbaca:",len(data["products"]))
print(data["notice"])
for error in data["errors"]:
    print(error["url"],"—",error["message"])
raise SystemExit(0 if data["products"] else 1)
