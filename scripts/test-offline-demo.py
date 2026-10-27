"""Exercise the standalone document without a server or network requests.

set_content is used because the managed cloud browser blocks file:// navigation.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

root=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path="/usr/bin/chromium",headless=True,args=["--no-sandbox"])
    page=browser.new_page(viewport={"width":1440,"height":1050},accept_downloads=True)
    errors=[];requests=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.on("request",lambda r:requests.append(r.url))
    page.set_content((root/"outputs/Rantai-Buka-Langsung.html").read_text())
    expect(page.locator(".activity-cell")).to_have_count(9)
    for code,name in [("sidogiri","KOPONTRES SIDOGIRI"),("unsiq","UNSIQ WONOSOBO"),("ashavin","PT ASHAVIN PANDAWA MEDIKA INDONESIA"),("surya","BPR BANK SURYA YUDHA"),("kospin","KOSPIN JASA")]:
        page.locator("#preset").select_option(code)
        expect(page.locator("#result-company")).to_have_text(name)
    page.locator("#company").fill("Contoh Perusahaan Saya")
    page.locator("#analyze-button").click()
    expect(page.locator("#result-company")).to_have_text("Contoh Perusahaan Saya")
    page.locator("#open-import").click()
    page.locator("#import-text").fill("STANDARD_NAME,WITEL_HO,GROUP4,GROUP5,DESC2\nTEST COMPANY,WITEL,VPN,VPN,Intranet")
    page.locator("#parse-import").click()
    expect(page.locator("#apply-import")).to_be_visible()
    page.locator("#apply-import").click()
    page.locator("#analyze-button").click()
    expect(page.locator("#result-company")).to_have_text("TEST COMPANY")
    page.locator("#preset").select_option("surya")
    expect(page.locator("#result-company")).to_have_text("BPR BANK SURYA YUDHA")
    page.locator("#solution-view").click()
    expect(page.locator(".solution-item.existing")).to_have_count(4)
    page.locator("#activity-view").click()
    page.locator("#export-button").click()
    with page.expect_download() as event:
        page.locator("#export-svg").click()
    event.value.save_as(root/".runtime/offline-export.svg")
    page.locator("#guide-nav").click()
    expect(page.locator("#guide-dialog")).to_be_visible()
    page.locator('[data-close="guide-dialog"]').click()
    page.screenshot(path=str(root/".runtime/offline-desktop.png"),full_page=True)
    assert not errors,errors
    assert not requests,requests
    browser.close()
print("PASS: standalone HTML, five companies, custom input, CSV import, solution layer, SVG export, guide; no server, network requests, or JS errors.")
