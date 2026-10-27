"""Build a self-contained, explicitly unresearched demo requiring no server."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bs4 import BeautifulSoup
from app.domain import AnalysisInput, EXAMPLES, SECTORS, sample_analysis
from app.catalog import read_catalog, enrich_analysis

templates = {}
catalog = read_catalog()
for example in EXAMPLES:
    data = AnalysisInput.model_validate({k: v for k, v in example.items() if k != "id"})
    templates[data.sector] = enrich_analysis(sample_analysis(data).model_dump(),data.model_dump(),catalog)
payload = json.dumps({"companies": EXAMPLES, "sectors": SECTORS, "templates": templates,"catalog":catalog}, ensure_ascii=False).replace("<", "\\u003c")
shim = r'''
const offlineData = PAYLOAD;
function readOfflineTable(raw) {
  if(raw.length>150000)throw Error("Maksimal ukuran tabel 150 KB.");
  raw=raw.replace(/^\uFEFF/,"").trim();
  const first=raw.split(/\r?\n/)[0]||"", delimiter=first.includes("\t")?"\t":first.includes(";")?";":",";
  const rows=[];let row=[],cell="",quoted=false;
  for(let i=0;i<raw.length;i++){
    const c=raw[i];
    if(c==='"'){if(quoted&&raw[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}
    else if(!quoted&&c===delimiter){row.push(cell);cell="";}
    else if(!quoted&&(c==="\n"||c==="\r")){if(c==="\r"&&raw[i+1]==="\n")i++;row.push(cell);rows.push(row);row=[];cell="";}
    else cell+=c;
  }
  if(quoted)throw Error("Tanda kutip CSV belum ditutup.");
  if(cell||row.length){row.push(cell);rows.push(row);}
  const header=(rows.shift()||[]).map(x=>x.trim().toUpperCase());
  const keys=["STANDARD_NAME","WITEL_HO","GROUP4","GROUP5","DESC2"];
  if(keys.some(k=>!header.includes(k)))throw Error("Header wajib: "+keys.join(", "));
  if(rows.length>1000)throw Error("Maksimal 1.000 baris tabel.");
  const companies=new Map();let state={};
  for(const row of rows){
    const v=Object.fromEntries(keys.map(k=>[k,(row[header.indexOf(k)]||"").trim()]));
    if(v.STANDARD_NAME&&v.STANDARD_NAME!==state.STANDARD_NAME)state={};
    if(v.GROUP4&&v.GROUP4!==state.GROUP4)state.GROUP5="";
    for(const k of keys.slice(0,-1))if(v[k])state[k]=v[k];
    if(!state.STANDARD_NAME)continue;
    if(!companies.has(state.STANDARD_NAME))companies.set(state.STANDARD_NAME,{company:state.STANDARD_NAME,witel:state.WITEL_HO||"",services:[]});
    const c=companies.get(state.STANDARD_NAME);c.witel=state.WITEL_HO||"";
    if(state.GROUP4||state.GROUP5){const service={group4:state.GROUP4||"",group5:state.GROUP5||state.GROUP4||"",description:v.DESC2};if(!c.services.some(s=>JSON.stringify(s)===JSON.stringify(service)))c.services.push(service);}
  }
  if(!companies.size)throw Error("Tabel belum memuat nama perusahaan.");
  if([...companies.values()].some(c=>c.services.length>80))throw Error("Maksimal 80 baris layanan per perusahaan.");
  return {companies:[...companies.values()]};
}
async function api(path,data){
  if(path==="/api/examples")return structuredClone(offlineData);
  if(path==="/api/preview"){
    if(!data.company||data.company.length<2)throw Error("Isi nama perusahaan minimal dua karakter.");
    const analysis=structuredClone(offlineData.templates[data.sector]);
    // Snapshot examples are not rematched against newly edited customer input offline.
    for(const o of analysis.opportunities){o.matched_products=[];o.product_ids=[];}
    return {mode:"sample",company:structuredClone(data),analysis,catalog:structuredClone(offlineData.catalog),sources:[],model:null,generated_at:new Date().toISOString(),warnings:["Contoh offline: kerangka hipotesis sektor, belum diriset melalui Google dan belum diproses LLM. Perubahan nama dan layanan tidak memverifikasi profil perusahaan.","Data layanan berasal dari input; kontrak aktif dan kebutuhan perusahaan perlu dikonfirmasi.","Pencocokan produk resmi dengan data yang diedit memerlukan aplikasi lengkap; versi offline hanya menyertakan snapshot katalog jika pernah terbaca."]};
  }
  if(path==="/api/import")return readOfflineTable(data.text);
  throw Error("Fitur ini memerlukan aplikasi lengkap. File ini hanya contoh offline.");
}
'''.replace("PAYLOAD", payload)
js = (ROOT / "app/static/app.js").read_text()
js, count = re.subn(r"async function api\(path, data\) \{.*?\n\}\n", lambda _: shim + "\n", js, count=1, flags=re.S)
assert count == 1
js, count = re.subn(r"async function checkRuntime\(\) \{.*?\n\}\n", '''async function checkRuntime(){
  $("runtime-status").querySelector("span:nth-child(2)").textContent="Contoh offline · tanpa instalasi";
  $("guide-runtime").textContent="Versi ini berjalan langsung di browser. Tidak mengakses Google atau LLM.";
}
''', js, count=1, flags=re.S)
assert count == 1
js, count = re.subn(r"async function analyze\(event\) \{.*?\n\}\n\nfunction download", '''async function analyze(event){
  event.preventDefault();await preview();toast("Diagram contoh diperbarui. Belum merupakan hasil riset Google atau AI.");
}

function download''', js, count=1, flags=re.S)
assert count == 1
js = js.replace('Jalankan “Riset & buat analisis” untuk menambahkan sumber Google dan analisis model lokal.', 'File ini tidak melakukan riset Google atau analisis AI. Diagram yang ditampilkan adalah kerangka contoh sektor.')
soup = BeautifulSoup((ROOT / "app/static/index.html").read_text(), "html.parser")
soup.title.string = "Rantai — Buka Langsung (Contoh Offline)"
for el in soup.select("link[rel=stylesheet],script[src]"):
    el.decompose()
style = soup.new_tag("style")
style.string = (ROOT / "app/static/style.css").read_text()
soup.head.append(style)
csp = soup.new_tag("meta", attrs={"http-equiv":"Content-Security-Policy","content":"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; connect-src 'none'; base-uri 'none'; form-action 'none'"})
soup.head.append(csp)
soup.select_one(".brand")["href"] = "#"
soup.select_one(".process").replace_with(BeautifulSoup('<div class="process"><div class="process-last"><b>✓</b><span>CONTOH OFFLINE · TANPA INSTALASI</span><span>Pilih perusahaan → Ubah data → Lihat diagram</span></div></div>',"html.parser"))
soup.select_one("#analyze-button span").string = "Perbarui diagram contoh"
soup.select_one("#preview-button")["hidden"] = ""
soup.select_one("#refresh-catalog")["disabled"] = ""
soup.select_one("#refresh-catalog").string = "Pembaruan & pencocokan katalog memerlukan aplikasi lengkap"
soup.select_one("#company-form > .form-note").string = "Contoh ini belum melakukan riset Google atau analisis AI."
soup.select_one(".privacy-note p").string = "Data tetap di browser ini. File contoh tidak mengirim data, mengakses Google, atau menjalankan AI."
guide=soup.select_one("#guide-dialog")
guide.clear()
guide.append(BeautifulSoup('''<div class="dialog-header"><div><span class="small-label">TANPA TERMINAL</span><h2>Coba diagramnya langsung.</h2></div><button data-close="guide-dialog" class="dialog-close" aria-label="Tutup panduan">×</button></div><div class="guide-steps"><article><b>01</b><div><h3>Pilih perusahaan</h3><p>Gunakan pilihan “Pilih contoh pelanggan” untuk melihat kelima contoh dari data yang kamu kirim.</p></div></article><article><b>02</b><div><h3>Sesuaikan data</h3><p>Ubah nama, segmen, atau layanan, lalu klik “Perbarui diagram contoh”. Ini memperbarui kerangka sektor, bukan meneliti perusahaan.</p></div></article><article><b>03</b><div><h3>Lihat dan simpan diagram</h3><p>Klik Aktivitas atau Solusi. Pilih kotak diagram untuk melihat detail. Gunakan Ekspor untuk menyimpan SVG, JSON, CSV, atau mencetak PDF.</p></div></article></div><div class="guide-note"><strong>Ini versi contoh offline</strong><p>Google dan LLM tidak berjalan di file ini. Riset otomatis tersedia pada aplikasi lengkap setelah akses Google dan unduhan model lokal siap. Semua contoh masih hipotesis yang perlu dikonfirmasi.</p></div><button id="refresh-status" class="secondary-button">Informasi versi contoh</button><p id="guide-runtime" class="form-note"></p>''',"html.parser"))
script=soup.new_tag("script")
script.string=js
soup.body.append(script)
output=ROOT / "outputs/Rantai-Buka-Langsung.html"
output.write_text(str(soup))
print(f"Built {output.name} ({output.stat().st_size:,} bytes); no server or network required.")
