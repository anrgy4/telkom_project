"""Public Google research; blocked requests are reported, never bypassed."""
import asyncio
import ipaddress
import os
import shutil
import socket
from datetime import datetime, timezone
from urllib.parse import parse_qs, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup


class ResearchError(Exception):
    pass


class JavaScriptRequired(ResearchError):
    pass


HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; IVCAResearch/1.0)", "Accept-Language": "id-ID,id;q=0.9,en;q=0.7"}


async def public_url(url: str) -> bool:
    """Reject local/private destinations, including each redirect target."""
    try:
        p = urlsplit(url)
        if p.scheme not in ("http", "https") or p.username or p.password or p.port not in (None, 80, 443):
            return False
        host = p.hostname or ""
        if host.lower() in ("localhost", "metadata.google.internal") or host.endswith(".local"):
            return False
        results = await asyncio.wait_for(asyncio.get_running_loop().getaddrinfo(host, p.port or 443, type=socket.SOCK_STREAM), timeout=5)
        return bool(results) and all(ipaddress.ip_address(x[4][0]).is_global for x in results)
    except (ValueError, OSError, asyncio.TimeoutError):
        return False


async def bounded_html(client: httpx.AsyncClient, url: str, *, validate=True) -> str:
    for _ in range(4):
        if validate and not await public_url(url):
            raise ResearchError("Alamat sumber bukan halaman publik yang diizinkan.")
        async with client.stream("GET", url, follow_redirects=False) as r:
            if r.status_code in (301, 302, 303, 307, 308):
                url = urljoin(url, r.headers.get("location", ""))
                continue
            r.raise_for_status()
            if not any(c in r.headers.get("content-type", "").lower() for c in ("text/html", "text/plain")):
                raise ResearchError("Sumber bukan halaman teks/HTML.")
            chunks, size = [], 0
            async for part in r.aiter_bytes():
                size += len(part)
                if size > 1_000_000:
                    raise ResearchError("Halaman sumber melebihi batas 1 MB.")
                chunks.append(part)
            return b"".join(chunks).decode(r.encoding or "utf-8", errors="replace")
    raise ResearchError("Terlalu banyak pengalihan sumber.")


def parse_google(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    if soup.select_one('form[action*="/sorry/"]') or any(t in soup.get_text(" ", strip=True).lower() for t in ["our systems have detected unusual traffic", "unusual traffic from your computer", "sebelum melanjutkan ke google", "lalu lintas yang tidak wajar"]):
        raise ResearchError("Google meminta verifikasi/CAPTCHA. Permintaan dihentikan; coba kembali nanti.")
    if soup.select_one('a[href*="/httpservice/retry/enablejs"]'):
        raise JavaScriptRequired("Google mengembalikan halaman yang memerlukan JavaScript, bukan hasil pencarian.")
    results, seen = [], set()
    for heading in soup.select("h3"):
        anchor = heading.find_parent("a") or heading.find("a")
        if not anchor:
            continue
        href = anchor.get("href", "")
        if href.startswith("/url?") or href.startswith("https://www.google.com/url?"):
            q = parse_qs(urlsplit(href).query)
            href = q.get("q", q.get("url", [""]))[0]
        p = urlsplit(href)
        if p.scheme not in ("http", "https") or not p.hostname or p.hostname in ("google.com", "www.google.com") or href in seen:
            continue
        seen.add(href)
        parent = anchor.parent
        for _ in range(3):
            if parent and parent.parent and len(parent.get_text(" ", strip=True)) < 150:
                parent = parent.parent
        snippet = parent.get_text(" ", strip=True)[:1600] if parent else heading.get_text(" ", strip=True)
        results.append({"title": heading.get_text(" ", strip=True)[:250], "url": href, "snippet": snippet})
    return results[:5]


async def rendered_google(url):
    """Ordinary JS rendering only. No stealth, CAPTCHA solving, or cert bypass."""
    from playwright.async_api import async_playwright, Error, TimeoutError as BrowserTimeout
    try:
        async with async_playwright() as p:
            executable = os.getenv("CHROMIUM_PATH") or shutil.which("chromium") or shutil.which("chromium-browser")
            options = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
            if executable:
                options["executable_path"] = executable
            browser = await p.chromium.launch(**options)
            try:
                context = await browser.new_context(locale="id-ID")
                async def route_request(route):
                    host = urlsplit(route.request.url).hostname or ""
                    allowed = host in ("www.google.com", "google.com", "www.gstatic.com", "ssl.gstatic.com")
                    if not allowed or route.request.resource_type in ("image", "media", "font", "stylesheet"):
                        await route.abort()
                    else:
                        await route.continue_()
                await context.route("**/*", route_request)
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                try:
                    await page.wait_for_selector('h3, form[action*="/sorry/"], iframe[src*="recaptcha"]', timeout=15000)
                except BrowserTimeout:
                    pass
                html = await page.content()
                results = parse_google(html)
                if not results:
                    raise ResearchError("Google belum mengembalikan hasil setelah rendering JavaScript. Tunggu akses Google pulih; halaman verifikasi/consent tidak dilewati.")
                return results
            finally:
                await browser.close()
    except JavaScriptRequired as exc:
        raise ResearchError("Halaman Google masih meminta JavaScript/verifikasi. Tunggu akses Google pulih, lalu coba lagi.") from exc
    except Error as exc:
        raise ResearchError("Chromium belum dapat membaca Google. Periksa instalasi Chromium, izin jaringan, dan trust CA proxy tanpa menonaktifkan TLS. Tunggu akses Google pulih bila halaman meminta verifikasi.") from exc


async def search_google(client, query):
    url = str(httpx.URL("https://www.google.com/search", params={"q": query, "hl": "id", "num": "5", "gbv": "1"}))
    try:
        return parse_google(await bounded_html(client, url, validate=False))
    except JavaScriptRequired:
        return await asyncio.wait_for(rendered_google(url), timeout=50)


async def research(company: str, sector: str, notify):
    query = f'"{company}" profil perusahaan {sector}'
    await notify("search", "Mencari informasi publik di Google…")
    async with httpx.AsyncClient(headers=HEADERS, timeout=20) as client:
        try:
            sources = await search_google(client, query)
        except (httpx.HTTPError, ResearchError, asyncio.TimeoutError) as exc:
            if isinstance(exc, ResearchError):
                raise
            raise ResearchError("Google belum dapat diakses (kebijakan jaringan, koneksi, atau respons HTTP). Izinkan www.google.com di pengaturan lingkungan. Tidak ada hasil riset yang direkayasa.") from exc
        if not sources:
            raise ResearchError("Google tidak mengembalikan hasil yang dapat dibaca. Coba nama badan usaha yang lebih spesifik; format halaman Google juga dapat berubah.")
        await notify("sources", f"Membaca {len(sources)} sumber hasil pencarian…")

        async def enrich(index, src):
            src = {**src, "id": f"S{index+1}", "retrieved_at": datetime.now(timezone.utc).isoformat(), "kind": "search_snippet", "text": src["snippet"]}
            try:
                page = await asyncio.wait_for(bounded_html(client, src["url"]), timeout=20)
                soup = BeautifulSoup(page, "html.parser")
                for elem in soup.select("script,style,nav,footer,header,noscript,form"):
                    elem.decompose()
                text = " ".join((soup.find("main") or soup.find("article") or soup).get_text(" ", strip=True).split())
                if len(text) < 100:
                    raise ResearchError("Teks halaman terlalu pendek.")
                src.update(text=text[:5000], kind="page", fetch_status="Halaman terbaca")
            except (httpx.HTTPError, ResearchError, asyncio.TimeoutError, ValueError):
                src["fetch_status"] = "Hanya cuplikan Google; halaman sumber tidak terbaca"
            return src

        sources = await asyncio.gather(*(enrich(i, s) for i, s in enumerate(sources)))
    return {"query": query, "sources": sources}
