"""Browser contract test with SYNTHETIC catalogue fixtures; not a live-site claim."""
import json
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright, expect

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from app.catalog import parse_catalog_page,enrich_analysis,empty_catalog
from app.domain import AnalysisInput,EXAMPLES,sample_analysis

customer=AnalysisInput.model_validate({k:v for k,v in EXAMPLES[0].items() if k!="id"})
stamp="2026-10-27T00:00:00+00:00"
products,_=parse_catalog_page('<main><h1>ASTINet</h1><p>Fixture pengujian monitoring jaringan internet, bukan hasil pembacaan situs sebenarnya.</p></main>',"https://www.telkomsolution.co.id/produk/fixture-astinet",stamp)
catalog=empty_catalog();catalog.update(status="available",products=products,updated_at=stamp,notice="DATA FIXTURE PENGUJIAN — bukan observasi situs resmi.")
analysis=enrich_analysis(sample_analysis(customer).model_dump(),customer.model_dump(),catalog)
result={"mode":"sample","company":customer.model_dump(),"analysis":analysis,"catalog":catalog,"sources":[],"model":None,"generated_at":stamp,"warnings":["Fixture untuk menguji UI, bukan riset nyata."]}
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path="/usr/bin/chromium",headless=True,args=["--no-sandbox"])
    page=browser.new_page(viewport={"width":1440,"height":1080},accept_downloads=True)
    errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
    page.route("**/api/preview",lambda route:route.fulfill(json=result))
    page.route("**/api/catalog/refresh",lambda route:route.fulfill(json=catalog))
    page.route("**/api/match",lambda route:route.fulfill(json={"analysis":analysis,"catalog":catalog}))
    page.goto("http://127.0.0.1:8000")
    expect(page.locator(".activity-cell")).to_have_count(9)
    page.locator('[data-tab="opportunities"]').click()
    expect(page.locator("#opportunities-list .product-card")).to_have_count(1)
    expect(page.locator("#opportunities-list .product-status")).to_contain_text("Existing menurut input")
    expect(page.locator("#opportunities-list .product-card a")).to_have_attribute("href",products[0]["source_url"])
    page.locator('[data-tab="canvas"]').click();page.locator("#solution-view").click()
    expect(page.locator(".solution-item").filter(has_text="ASTINet")).to_have_count(2)
    page.locator('[data-tab="catalog"]').click()
    expect(page.locator("#catalog-list .product-card")).to_have_count(1)
    expect(page.locator("#catalog-status")).to_contain_text("DATA FIXTURE")
    page.locator("#company").fill("Input baru belum dianalisis")
    page.locator("#refresh-catalog").click()
    expect(page.locator("#refresh-catalog")).to_have_text("Perbarui katalog resmi")
    expect(page.locator("#dirty-banner")).to_be_visible()
    expect(page.locator("#result-company")).to_have_text(customer.company)
    page.locator("#export-button").click()
    with page.expect_download() as event:page.locator("#export-csv").click()
    event.value.save_as(root/".runtime/catalog-test.csv")
    csv=(root/".runtime/catalog-test.csv").read_text(encoding="utf-8-sig")
    assert products[0]["source_url"] in csv
    assert "existing_in_input" in csv
    page.set_viewport_size({"width":390,"height":844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert not errors,errors
    browser.close()
print("PASS: synthetic catalogue matching UI, existing status, official links, solution diagram, manual refresh, dirty snapshot preserved, CSV provenance, mobile; no JS errors. Live websites not tested by this fixture.")
