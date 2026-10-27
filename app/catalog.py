"""Bounded ingestion of the user's official catalogues and explainable matching.

No product names are invented or shipped as verified without a fetched source.
Customer data is never sent to catalogue websites.
"""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import unicodedata
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlsplit, urlunsplit
from typing import Literal

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field

from .research import HEADERS

HOSTS = {"www.telkomsolution.co.id", "telkomsolution.co.id", "indibiz.co.id", "www.indibiz.co.id"}
SEEDS = ["https://www.telkomsolution.co.id/", "https://www.telkomsolution.co.id/produk", "https://indibiz.co.id/"]
SITEMAPS = ["https://www.telkomsolution.co.id/sitemap.xml", "https://indibiz.co.id/sitemap.xml"]
CACHE = Path(__file__).resolve().parents[1] / ".runtime/product-catalog.json"
SNAPSHOT = Path(__file__).resolve().parent / "data/product-catalog.json"
PRODUCT_PATH = re.compile(r"/(?:produk|products?|solusi|solutions?|layanan|services?)(?:/|$)", re.I)
EXCLUDED_PATH = re.compile(r"/(?:blog|artikel|berita|news|login|register|daftar|member|my|berlangganan|pilihan-paket|leads|health-check|kontak|contact|cart|checkout)(?:/|$)", re.I)
sync_lock = asyncio.Lock()


class Product(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(max_length=40)
    name: str = Field(min_length=2, max_length=180)
    description: str = Field(min_length=30, max_length=3000)
    source_url: str = Field(max_length=1000)
    observed_at: str
    entry_type: str
    evidence_quote: str = Field(min_length=20, max_length=500)
    aliases: list[str] = Field(default_factory=list, max_length=8)
    availability: Literal["listed","maintenance","coming_soon"] = "listed"


def canonical(url, base=""):
    try:
        p = urlsplit(urljoin(base, url))
        if p.scheme not in ("https", "http") or p.hostname not in HOSTS or p.username or p.password or p.port not in (None, 80, 443):
            return None
        if EXCLUDED_PATH.search(p.path):
            return None
        return urlunsplit(("https", p.hostname, p.path.rstrip("/") or "/", "", ""))
    except ValueError:
        return None


def empty_catalog():
    return {"status":"empty", "products":[], "updated_at":None, "seeds":SEEDS, "pages_read":0, "errors":[], "notice":"Katalog resmi belum berhasil dibaca. Tidak ada produk yang dibuat-buat. Klik Perbarui katalog saat akses situs tersedia."}


def read_catalog(path=None):
    path = Path(path) if path is not None else (CACHE if CACHE.exists() else SNAPSHOT)
    try:
        data = json.loads(path.read_text())
        products = [Product.model_validate(p).model_dump() for p in data["products"]]
        if any(not canonical(p["source_url"]) for p in products):
            raise ValueError("Non-official source")
        # Revalidate cached records after parser improvements. Editorial/event
        # pages containing the word "produk" are not catalogue products.
        products = [p for p in products if PRODUCT_PATH.search(urlsplit(p["source_url"]).path)]
        for p in products:
            identifier = urlsplit(p["source_url"]).path.rstrip("/").split("/")[-1]
            if identifier not in p["aliases"] and len(p["aliases"]) < 8:
                p["aliases"].append(identifier)
            if "/maintenance/" in urlsplit(p["source_url"]).path:
                p["availability"] = "maintenance"
        data["products"] = products
        return data
    except (OSError, ValueError, KeyError, TypeError):
        return empty_catalog()


def plain(value):
    return " ".join(BeautifulSoup(str(value or ""), "html.parser").get_text(" ", strip=True).split())


def parse_catalog_page(html, url, observed_at):
    """Return evidence-backed records and links; generic hub pages aren't products."""
    if urlsplit(url).path.endswith(".xml"):
        try:
            tree = ET.fromstring(html)
            links = []
            for element in tree.iter():
                if element.tag.split("}")[-1] == "loc":
                    target = canonical(element.text or "",url)
                    if target and (PRODUCT_PATH.search(urlsplit(target).path) or urlsplit(target).path.endswith(".xml")) and target not in links:
                        links.append(target)
            return [],links[:200]
        except ET.ParseError:
            return [],[]
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.select("a[href]"):
        href = canonical(a["href"], url)
        if href and PRODUCT_PATH.search(urlsplit(href).path) and href not in links:
            links.append(href)
    records = []

    def record(name, description, source, kind, aliases=(), availability="listed"):
        source = canonical(source, url)
        name, description = plain(name)[:180], plain(description)[:3000]
        if not source or len(name) < 2 or len(description) < 30:
            return
        product_id = "P-" + hashlib.sha256((source + "|" + name.casefold()).encode()).hexdigest()[:16]
        records.append(Product(id=product_id,name=name,description=description,source_url=source,observed_at=observed_at,entry_type=kind,evidence_quote=description[:500],aliases=[plain(a)[:180] for a in aliases if plain(a)][:8],availability=availability).model_dump())

    def schema(node):
        if isinstance(node, list):
            for child in node:
                schema(child)
        elif isinstance(node, dict):
            types = node.get("@type", [])
            types = [types] if isinstance(types, str) else types
            if isinstance(types, list) and any(t in ("Product", "Service") for t in types):
                # The fetched page is the evidence location, not a JSON-supplied URL.
                aliases = node.get("alternateName", [])
                record(node.get("name", ""),node.get("description", ""),url,"structured_product",[aliases] if isinstance(aliases,str) else aliases if isinstance(aliases,list) else [])
            for key in ("@graph", "mainEntity", "itemListElement", "item"):
                if key in node:
                    schema(node[key])
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            schema(json.loads(script.get_text()))
        except (ValueError, TypeError):
            continue
    # IndiBiz publishes the actual product fields in its public SSR payload.
    # Use those fields rather than an SEO title such as "Pencatatan Otomatis".
    next_data = soup.find("script",id="__NEXT_DATA__")
    if next_data and urlsplit(url).hostname in {"indibiz.co.id","www.indibiz.co.id"} and "/produk/" in urlsplit(url).path:
        try:
            detail = json.loads(next_data.get_text())["props"]["pageProps"].get("productDetail")
            if isinstance(detail,dict):
                if detail.get("isActive") is False:
                    return [],links[:100]
                flags = detail.get("status") if isinstance(detail.get("status"),dict) else {}
                availability = "maintenance" if flags.get("isMaintenance") or "/maintenance/" in urlsplit(url).path else "coming_soon" if flags.get("isComingSoon") else "listed"
                record(detail.get("name", ""),detail.get("description") or detail.get("subtitle", ""),url,"official_product_payload",[detail.get("code", ""),detail.get("slug", "")],availability)
        except (ValueError,KeyError,TypeError):
            pass
    for elem in soup.select("script,style,nav,footer,header,noscript,form"):
        elem.decompose()
    main = soup.find("main") or soup.find("article") or soup
    heading = main.find("h1")
    path = urlsplit(url).path
    if not records and PRODUCT_PATH.search(path) and len(path.strip("/").split("/")) >= 2:
        name = heading.get_text(" ",strip=True) if heading else ""
        if not name or name.casefold() in {"product detail page","product detail","detail produk","product page","produk","solusi"}:
            title_meta = soup.select_one('meta[property="og:title"]')
            name = title_meta.get("content", "") if title_meta else (soup.title.get_text(" ",strip=True) if soup.title else "")
            name = re.split(r"\s+[|]\s+",name)[0].strip()
            if name.casefold() in {"product detail page","product detail","detail produk","product page","produk","solusi"}:
                name = ""
        paragraphs = [p.get_text(" ",strip=True) for p in main.select("p") if len(p.get_text(" ",strip=True)) > 25]
        meta = soup.select_one('meta[name="description"],meta[property="og:description"]')
        description = " ".join(paragraphs[:8]) or (meta.get("content", "") if meta else "")
        record(name,description,url,"official_solution_page")
    return records, links[:100]


async def fetch_official(client, url):
    for _ in range(4):
        # Only four hardcoded official hostnames can be requested, including
        # every redirect. Let the configured HTTPS proxy resolve those hosts;
        # cloud machines may not have working local DNS for public websites.
        if not canonical(url):
            raise ValueError("Alamat bukan sumber resmi publik yang diizinkan")
        async with client.stream("GET",url,follow_redirects=False) as response:
            if response.status_code in (301,302,303,307,308):
                target = canonical(response.headers.get("location", ""),url)
                if not target:
                    raise ValueError("Pengalihan keluar dari situs resmi ditolak")
                url = target
                continue
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type and not (urlsplit(url).path.endswith(".xml") and "xml" in content_type):
                raise ValueError("Halaman bukan HTML")
            chunks, size = [], 0
            async for part in response.aiter_bytes():
                size += len(part)
                if size > 2_000_000:
                    raise ValueError("Halaman melebihi 2 MB")
                chunks.append(part)
            return b"".join(chunks).decode(response.encoding or "utf-8",errors="replace"),url
    raise ValueError("Terlalu banyak pengalihan")


async def render_official(url):
    from playwright.async_api import async_playwright, TimeoutError as BrowserTimeout
    async with async_playwright() as p:
        options = {"headless":True,"args":["--no-sandbox","--disable-dev-shm-usage"]}
        executable = os.getenv("CHROMIUM_PATH") or shutil.which("chromium") or shutil.which("chromium-browser")
        if executable:
            options["executable_path"] = executable
        browser = await p.chromium.launch(**options)
        try:
            page = await browser.new_page()
            async def route_request(route):
                if urlsplit(route.request.url).hostname not in HOSTS or route.request.resource_type in ("image","media","font","stylesheet"):
                    await route.abort()
                else:
                    await route.continue_()
            await page.route("**/*", route_request)
            await page.goto(url,wait_until="domcontentloaded",timeout=20000)
            try:
                await page.wait_for_function("document.querySelector('h1') && document.querySelectorAll('a[href]').length > 4",timeout=8000)
            except BrowserTimeout:
                pass
            if not canonical(page.url):
                raise ValueError("Browser keluar dari situs resmi")
            return await page.content(),page.url
        finally:
            await browser.close()


async def refresh_catalog(path=None, *, max_pages=120):
    """No customer input; at most 120 public pages, batches of three."""
    if sync_lock.locked():
        raise RuntimeError("Pembaruan katalog sedang berjalan. Tunggu sampai selesai.")
    async with sync_lock:
        old = read_catalog(path)
        observed_at = datetime.now(timezone.utc).isoformat()
        pending, visited, products, errors = list(SITEMAPS)+list(SEEDS), set(), {}, []
        rendered = 0
        async with httpx.AsyncClient(headers=HEADERS,timeout=15) as client:
            async def get(url):
                try:
                    html,final = await asyncio.wait_for(fetch_official(client,url),timeout=20)
                    return url,html,final,None
                except Exception as exc:
                    return url,None,url,f"Sumber tidak terbaca ({type(exc).__name__}); periksa akses jaringan/TLS."
            while pending and len(visited) < max_pages:
                batch = []
                while pending and len(batch) < 3 and len(visited) < max_pages:
                    url = pending.pop(0)
                    if url not in visited:
                        visited.add(url);batch.append(url)
                for original,html,final,error in await asyncio.gather(*(get(url) for url in batch)):
                    if error:
                        errors.append({"url":original,"message":error});continue
                    records, links = parse_catalog_page(html,final,observed_at)
                    discovered_detail = any(urlsplit(link).hostname==urlsplit(final).hostname and PRODUCT_PATH.search(urlsplit(link).path) and len(urlsplit(link).path.strip("/").split("/"))>=2 for link in pending)
                    if not records and not any(len(urlsplit(link).path.strip("/").split("/")) >= 2 for link in links) and not urlsplit(final).path.endswith(".xml") and not discovered_detail and rendered < 4:
                        rendered += 1
                        try:
                            html,final = await asyncio.wait_for(render_official(final),timeout=35)
                            records,links = parse_catalog_page(html,final,observed_at)
                        except Exception as exc:
                            errors.append({"url":original,"message":f"Rendering JavaScript tidak berhasil ({type(exc).__name__})."})
                    for record in records:
                        products[record["id"]] = record
                    pending.extend(link for link in links if link not in visited and link not in pending)
        data = {"status":"partial" if errors or pending else "available", "products":list(products.values()),"updated_at":observed_at,"last_attempt_at":observed_at,"seeds":SEEDS,"pages_read":len(visited)-len({e['url'] for e in errors}),"crawl_limit":max_pages,"limit_reached":bool(pending),"errors":errors,"notice":f"Katalog dibaca dari halaman dan sitemap resmi dengan batas {max_pages} halaman. Nama, deskripsi, dan URL adalah bukti sumber; kecocokan kebutuhan tetap usulan, bukan penawaran atau jaminan ketersediaan."}
        if not products:
            data["products"] = old["products"]
            data["updated_at"] = old["updated_at"]
            data["status"] = "stale" if old["products"] else "empty"
            data["notice"] = "Belum memperoleh produk baru dari situs resmi. " + ("Katalog lama dipertahankan; tanggal sumber harus diperiksa." if old["products"] else "Tidak ada produk yang dibuat-buat. Periksa izin jaringan atau struktur situs, lalu Perbarui katalog.")
        destination = Path(path) if path is not None else CACHE
        destination.parent.mkdir(parents=True,exist_ok=True)
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2))
        temporary.replace(destination)
        return data


STOP = set("dan atau yang untuk dengan pada dari dalam adalah layanan solusi produk product service business bisnis perusahaan pelanggan teknologi sistem management development activity kegiatan kebutuhan dapat membantu belum perlu saat serta bagaimana apa".split())
SYNONYMS = [set("jaringan network internet connectivity konektivitas broadband wifi astinet vpn".split()),set("monitoring pemantauan pantau monitor observability".split()),set("komunikasi communication messaging pesan whatsapp sms kontak contact omnichannel notifikasi".split()),set("keamanan security cybersecurity firewall antivirus".split()),set("kasir transaksi penjualan pos retail toko".split()),set("pendidikan education sekolah kampus akademik mahasiswa".split()),set("kesehatan health pasien medis klinik rumahsakit".split()),set("penyimpanan storage backup cloud server data".split())]


def tokens(text):
    text = unicodedata.normalize("NFKD",text).encode("ascii","ignore").decode().lower()
    return {word for word in re.findall(r"[a-z0-9]+",text) if len(word)>2 and word not in STOP}


def expanded(text):
    words = tokens(text)
    for group in SYNONYMS:
        if words & group:
            words = words | group
    return words


def identity_key(text):
    """Product identity keeps short qualifiers (IP) and word order."""
    ascii_text = unicodedata.normalize("NFKD",text).encode("ascii","ignore").decode().lower()
    return "".join(re.findall(r"[a-z0-9]+",ascii_text))


def match_products(opportunity, customer, products, limit=3):
    query = " ".join([opportunity["solution"],opportunity["rationale"]["text"],opportunity["discovery_question"]])
    words = expanded(query)
    focus = tokens(opportunity["solution"])
    focus_groups = [group for group in SYNONYMS if focus & group]
    context = tokens(customer.get("notes", ""))
    selected = set(opportunity.get("product_ids",[]))
    service_names = [s.get("group5") or s.get("group4", "") for s in customer.get("services",[])]
    existing = {identity_key(name) for name in service_names if name}
    existing_terms = [tokens(name) for name in service_names if name]
    ranked = []
    for raw in products:
        product = Product.model_validate(raw).model_dump()
        if not canonical(product["source_url"]) or product["availability"] != "listed":
            continue
        name_words = tokens(product["name"])
        product_words = tokens(product["name"]+" "+product["description"])
        overlap = words & product_words
        score = 15*len(focus & name_words)+10*len(focus & product_words)+2*len(overlap)+.2*len(context & product_words)
        # Distinguish servicing existing customers from acquisition/promotion.
        intent = ({"interaction","interaksi","pelayanan","keluhan","customer","contact","helpdesk","omnichannel"} if opportunity.get("activity")=="Service" else {"promosi","pemasaran","campaign","iklan","marketing","loyalty"} if opportunity.get("activity")=="Marketing & Sales" else set())
        score += 20*len(intent & name_words)+8*len(intent & product_words)
        model_selected = product["id"] in selected
        if not model_selected and any(not (group & product_words) for group in focus_groups):
            continue
        if not model_selected and not (words & name_words) and len(overlap)<2 and not focus_groups:
            continue
        names = [product["name"],*product["aliases"]]
        is_existing = any(identity_key(n) in existing for n in names)
        related_existing = any(e <= name_words for e in existing_terms if e)
        ranked.append((score + (1000 if model_selected else 0), {**product,"matched_terms":sorted(overlap)[:10],"match_method":"model_selected" if model_selected else "keyword_candidate","status":"existing_in_input" if is_existing else "possible_existing_family" if related_existing else "candidate_needs_validation","caveat":"Produk tercantum di sumber resmi; kebutuhan, paket, harga, cakupan, dan kecocokan perusahaan harus dikonfirmasi. Existing hanya menurut input, bukan kontrak aktif terverifikasi."}))
    ranked.sort(key=lambda row:(-row[0],row[1]["name"].casefold(),row[1]["id"]))
    return [row[1] for row in ranked[:limit]]


def enrich_analysis(analysis, customer, catalog):
    products = catalog.get("products",[])
    known = {p["id"] for p in products}
    for opportunity in analysis["opportunities"]:
        requested = opportunity.get("product_ids",[])
        opportunity["unknown_product_ids_removed"] = len([i for i in requested if i not in known])
        opportunity["product_ids"] = [i for i in requested if i in known]
        opportunity["matched_products"] = match_products(opportunity,customer,products)
    return analysis
