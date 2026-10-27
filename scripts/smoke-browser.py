"""Real browser smoke test against the running app. No Google/LLM calls are mocked here.

Requires a separate Playwright installation; uses the system Chromium.
"""
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

root = Path(__file__).resolve().parents[1]
artifacts = root / ".runtime" / "browser"
artifacts.mkdir(parents=True, exist_ok=True)
base_url = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=os.getenv("CHROMIUM_PATH", "/usr/bin/chromium"), args=["--no-sandbox"])
    page = browser.new_page(viewport={"width":1440,"height":1080}, accept_downloads=True)
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.goto(base_url)
    expect(page.locator(".activity-cell")).to_have_count(9)
    names = [("sidogiri","KOPONTRES SIDOGIRI"),("unsiq","UNSIQ WONOSOBO"),("ashavin","PT ASHAVIN PANDAWA MEDIKA INDONESIA"),("surya","BPR BANK SURYA YUDHA"),("kospin","KOSPIN JASA")]
    for value,name in names:
        page.locator("#preset").select_option(value)
        expect(page.locator("#result-company")).to_have_text(name)
        expect(page.locator("#analysis-kind")).to_contain_text("BELUM DIRISET")
        expect(page.locator(".activity-cell")).to_have_count(9)
    page.locator('.activity-cell[data-kind="primary"][data-index="1"]').click()
    expect(page.locator("#detail-dialog")).to_be_visible()
    expect(page.locator("#detail-title")).to_have_text("Operations")
    expect(page.locator("#detail-content")).to_contain_text("Hipotesis sektor")
    page.locator('[data-close="detail-dialog"]').click()
    page.locator("[data-eco=customers]").first.click()
    expect(page.locator("#detail-title")).to_have_text("Customer")
    page.locator('[data-close="detail-dialog"]').click()
    page.locator("#solution-view").click()
    expect(page.locator(".solution-item.existing")).to_have_count(2)
    page.locator('[data-tab="opportunities"]').click()
    expect(page.locator(".opportunity-card")).to_have_count(2)
    page.locator('[data-tab="sources"]').click()
    expect(page.locator("#tab-sources .empty-state")).to_contain_text("Belum ada riset publik")
    expect(page.locator("#data-table tr")).to_have_count(2)
    page.locator('[data-tab="canvas"]').click()
    page.locator("#activity-view").click()

    for button,ext in [("export-json","json"),("export-csv","csv"),("export-svg","svg")]:
        page.locator("#export-button").click()
        with page.expect_download() as event:
            page.locator("#"+button).click()
        event.value.save_as(artifacts/f"sample.{ext}")
    output=json.loads((artifacts/"sample.json").read_text())
    assert output["mode"]=="sample" and output["model"] is None and not output["sources"]
    svg=ET.parse(artifacts/"sample.svg").getroot()
    assert "BELUM DIRISET" in " ".join(svg.itertext())
    assert len(svg.findall(".//{http://www.w3.org/2000/svg}rect"))>20

    # Test a real missing-model error, without repeatedly querying Google.
    # Live research/inference is a separate readiness check.
    model_ready=page.request.get(base_url+"/api/health").json()["llm"]["ready"]
    if not model_ready:
        page.locator("#analyze-button").click()
        expect(page.locator("#error-card")).to_be_visible(timeout=15000)
        expect(page.locator("#analysis-kind")).to_contain_text("BELUM DIRISET")
        page.locator("#close-error").click()

    page.locator("#open-import").click()
    page.locator("#import-text").fill("name,service\nBad,VPN")
    page.locator("#parse-import").click()
    expect(page.locator("#import-error")).to_contain_text("Header wajib")
    page.locator("#import-text").fill("STANDARD_NAME\tWITEL_HO\tGROUP4\tGROUP5\tDESC2\nCOMPANY A\tW1\tVPN\tVPN\tIntranet\nCOMPANY B\tW2\tCloud\tCloud\tIDC")
    page.locator("#parse-import").click()
    expect(page.locator("#import-company-select option")).to_have_count(2)
    page.locator("#import-company-select").select_option("1")
    page.locator("#apply-import").click()
    expect(page.locator("#company")).to_have_value("COMPANY B")
    expect(page.locator("#dirty-banner")).to_be_visible()
    page.locator("#preview-button").click()
    expect(page.locator("#result-company")).to_have_text("COMPANY B")
    expect(page.locator("#existing-services")).to_contain_text("Cloud")

    # Escape input in the canvas and prevent spreadsheet formula execution.
    malicious="=XSS <img src=x onerror=alert(1)>"
    page.locator("#company").fill(malicious)
    page.locator("#preview-button").click()
    expect(page.locator("#result-company")).to_have_text(malicious)
    expect(page.locator("#result-company img")).to_have_count(0)
    page.locator("#export-button").click()
    with page.expect_download() as event:page.locator("#export-csv").click()
    event.value.save_as(artifacts/"formula-safe.csv")
    assert "\"'=XSS" in (artifacts/"formula-safe.csv").read_text(encoding="utf-8-sig")

    page.locator("#preset").select_option("surya")
    expect(page.locator("#result-company")).to_have_text("BPR BANK SURYA YUDHA")
    page.screenshot(path=str(artifacts/"desktop.png"),full_page=True)
    page.pdf(path=str(artifacts/"sample.pdf"),print_background=True,prefer_css_page_size=True)
    page.set_viewport_size({"width":390,"height":844})
    page.screenshot(path=str(artifacts/"mobile.png"),full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"),"Mobile page overflows"
    page.locator("#guide-nav").click()
    expect(page.locator("#guide-dialog")).to_be_visible()
    page.locator('[data-close="guide-dialog"]').click()
    assert not errors,errors
    browser.close()
    print("PASS: five companies, 9 activities, ecosystem details, solution layer, tabs, multi-company import, dirty state, XSS escaping, safe CSV, SVG/JSON/CSV/PDF exports, desktop/mobile layout; no JS errors.")
    print("Missing-model browser check:","SKIPPED (model available)" if model_ready else "PASS (real HTTP 503)")
    print(f"Artifacts: {artifacts}")
