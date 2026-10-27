"""Build a five-page PDF from the explicitly unresearched SVG examples."""
from pathlib import Path
import argparse
import html as html_module
import sys
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument("--solutions",action="store_true")
options=parser.parse_args()
out=root/"outputs"
slugs=["kopontres-sidogiri","unsiq-wonosobo","ashavin-pandawa-medika","bpr-bank-surya-yudha","kospin-jasa"]
prefix="contoh-solusi" if options.solutions else "contoh-ivca"
filename="Contoh-Matching-Produk-Resmi.pdf" if options.solutions else "Contoh-Diagram-5-Perusahaan.pdf"
references=[""]*len(slugs)
if options.solutions:
    sys.path.insert(0,str(root))
    from app.catalog import read_catalog,enrich_analysis
    from app.domain import AnalysisInput,EXAMPLES,sample_analysis
    catalog=read_catalog()
    for i,example in enumerate(EXAMPLES):
        customer=AnalysisInput.model_validate({k:v for k,v in example.items() if k!="id"})
        analysis=enrich_analysis(sample_analysis(customer).model_dump(),customer.model_dump(),catalog)
        products={p["source_url"]:p for o in analysis["opportunities"] for p in o["matched_products"]}
        references[i]='<div class="refs"><strong>Sumber kandidat produk resmi — kebutuhan perusahaan belum diriset</strong>'+''.join('<div>'+html_module.escape(p['name'])+' — '+html_module.escape(p['source_url'])+'</div>' for p in products.values())+'</div>'
html='<html><head><meta charset="utf-8"><style>@page{size:A3 landscape;margin:10mm}body{margin:0;font-family:Arial,sans-serif}section{break-after:page;height:270mm;display:flex;flex-direction:column;align-items:center;justify-content:center}section:last-child{break-after:auto}svg{width:100%;height:auto;max-height:'+('215mm' if options.solutions else '265mm')+'}.refs{width:100%;font-size:9px;line-height:1.6;color:#52654c;margin-top:12px}</style></head><body>'
html+=''.join('<section>'+(out/f"{prefix}-{slug}.svg").read_text()+references[i]+'</section>' for i,slug in enumerate(slugs))
html+='</body></html>'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path="/usr/bin/chromium",headless=True,args=["--no-sandbox"])
    page=browser.new_page()
    page.set_content(html)
    page.pdf(path=str(out/filename),print_background=True,prefer_css_page_size=True)
    browser.close()
print("Built "+filename)
