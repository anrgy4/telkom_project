import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from .domain import AnalysisInput, ModelAnalysis, EXAMPLES, SECTORS, parse_table, sample_analysis
from .llm import generate, model_name, model_status
from .research import ResearchError, research
from .catalog import read_catalog, refresh_catalog, enrich_analysis

app = FastAPI(title="Rantai · IVCA Workspace", version="1.0.0")
STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")
analysis_lock = asyncio.Lock()
logger = logging.getLogger(__name__)


@app.middleware("http")
async def response_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    return response


@app.get("/")
async def home():
    return FileResponse(STATIC / "index.html")


@app.get("/api/ready")
async def ready():
    # Starting the UI must not wait for Ollama or any external service.
    return {"status": "ok", "app": "rantai-ivca"}


@app.get("/api/health")
async def health():
    return {"status": "ok", "llm": await model_status(), "search": {"provider": "google_scraping", "javascript_renderer": "chromium"}}


@app.get("/api/examples")
async def examples():
    return {"companies": EXAMPLES, "sectors": SECTORS}


@app.get("/api/catalog")
async def get_catalog():
    return read_catalog()


@app.post("/api/catalog/refresh")
async def update_catalog():
    try:
        return await refresh_catalog()
    except RuntimeError as exc:
        raise HTTPException(409,str(exc)) from exc


class MatchInput(BaseModel):
    company: AnalysisInput
    analysis: ModelAnalysis


@app.post("/api/match")
async def rematch(data: MatchInput):
    catalog = read_catalog()
    return {"analysis":enrich_analysis(data.analysis.model_dump(),data.company.model_dump(),catalog),"catalog":catalog}


@app.post("/api/preview")
async def preview(data: AnalysisInput):
    catalog = read_catalog()
    return {
        "mode": "sample", "company": data.model_dump(), "analysis": enrich_analysis(sample_analysis(data).model_dump(),data.model_dump(),catalog),
        "catalog":catalog,
        "sources": [], "model": None, "generated_at": datetime.now(timezone.utc).isoformat(),
        "warnings": ["Contoh kerangka sektor, belum diriset dan belum diproses LLM. Seluruh aktivitas dan peluang adalah hipotesis.", "Data layanan dari pengguna belum memverifikasi kontrak aktif, pemetaan produk, atau nominal pendapatan."],
    }


class TableInput(BaseModel):
    text: str = Field(max_length=150_000)
    company: str = Field(default="", max_length=180)


@app.post("/api/import")
async def import_table(data: TableInput):
    try:
        return parse_table(data.text, data.company)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/analyze")
async def analyze(data: AnalysisInput):
    if analysis_lock.locked():
        raise HTTPException(409, "Satu analisis sedang berjalan. Tunggu selesai atau batalkan sebelum mencoba lagi.")
    status = await model_status()
    if not status["ready"]:
        raise HTTPException(503, f"{status['message']}. Jalankan Ollama dan unduh model {model_name()}. Lihat panduan pengaturan lokal.")

    async def stream():
        queue = asyncio.Queue()

        async def notify(stage, message):
            await queue.put({"type": "progress", "stage": stage, "message": message})

        async def run():
            try:
                async with analysis_lock:
                    research_result = await research(data.company.strip(), SECTORS[data.sector], notify)
                    await queue.put({"type": "research", **research_result})
                    catalog = read_catalog()
                    if not catalog["products"] and not catalog.get("last_attempt_at"):
                        await notify("catalog","Membaca katalog resmi Telkom Solution dan IndiBiz…")
                        catalog = await refresh_catalog()
                    result, downgraded = await generate(data, research_result["sources"], notify,catalog)
                    warnings = ["Analisis AI perlu ditinjau. Kutipan menunjukkan asal data, bukan verifikasi independen; cocokkan identitas perusahaan dan tanyakan hipotesis pada pelanggan.", "Existing = tercantum dalam input pelanggan; status Win/kontrak aktif belum diverifikasi."]
                    if downgraded:
                        warnings.append(f"{downgraded} klaim tanpa kutipan yang cocok ditandai ulang sebagai hipotesis.")
                    if not catalog["products"]:
                        warnings.append("Katalog resmi belum terbaca; belum ada pencocokan produk resmi yang bisa ditampilkan.")
                    elif catalog["status"] in ("stale","partial"):
                        warnings.append("Katalog tidak lengkap atau menggunakan cache; periksa tanggal dan halaman sumber produk.")
                    analysis = enrich_analysis(result.model_dump(),data.model_dump(),catalog)
                    await queue.put({"type": "result", "data": {"mode": "live", "company": data.model_dump(), "analysis": analysis,"catalog":catalog, "sources": research_result["sources"], "query": research_result["query"], "model": model_name(), "generated_at": datetime.now(timezone.utc).isoformat(), "warnings": warnings}})
            except ResearchError as exc:
                await queue.put({"type": "error", "message": str(exc)})
            except httpx.HTTPError:
                await queue.put({"type": "error", "message": "Permintaan ke Ollama lokal gagal atau melewati batas waktu. Periksa proses dan model Ollama; hasil contoh tidak dianggap hasil LLM."})
            except (ValueError, KeyError, ValidationError):
                await queue.put({"type": "error", "message": "Output model belum memenuhi struktur IVCA atau tidak lengkap. Coba lagi atau gunakan model lokal lebih besar. Tidak ada hasil yang dibuat seolah berhasil."})
            except Exception:
                logger.exception("Analysis failed")
                await queue.put({"type": "error", "message": "Analisis terhenti karena kesalahan internal. Periksa log aplikasi."})
            finally:
                await queue.put(None)

        task = asyncio.create_task(run())
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=10)
                except asyncio.TimeoutError:
                    yield json.dumps({"type": "heartbeat"}) + "\n"
                    continue
                if event is None:
                    break
                yield json.dumps(event, ensure_ascii=False) + "\n"
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    return StreamingResponse(stream(), media_type="application/x-ndjson", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"})
