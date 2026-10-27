"use strict";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const basisNames = {customer:"Data pelanggan", public:"Sumber publik", hypothesis:"Hipotesis sektor"};
let examples = [], sectors = {}, result = null, layer = "activity", controller = null, imported = [], activeTab = "canvas";
let dirty = false;
let previewVersion = 0;
let currentCatalog = {products:[],status:"empty",notice:"Katalog resmi belum dibaca."};

function safeUrl(url) { try { const u = new URL(url); return ["http:", "https:"].includes(u.protocol) && !u.username && !u.password ? u.href : "#"; } catch { return "#"; } }
function dot(basis) { return `<i class="basis-dot basis-${esc(basis)}" title="${esc(basisNames[basis] || basis)}"></i>`; }
function toast(text) { $("toast").textContent = text; $("toast").hidden = false; clearTimeout(toast.timer); toast.timer = setTimeout(() => $("toast").hidden = true, 4500); }
function showError(message) { $("error-message").textContent = message; $("error-card").hidden = false; }
function markDirty() { dirty = true; $("dirty-banner").hidden = !result; }
function dialog(id) { if (!$(id).open) $(id).showModal(); }

function addService(value = {}) {
  const row = document.createElement("div"); row.className = "service-entry";
  row.innerHTML = `<div class="service-fields"><input class="service-g4" aria-label="GROUP4 layanan" maxlength="120" placeholder="GROUP4" value="${esc(value.group4 || "")}"><input class="service-g5" aria-label="GROUP5 layanan" maxlength="120" placeholder="GROUP5" value="${esc(value.group5 || "")}"></div><input class="service-desc" aria-label="DESC2 layanan" maxlength="500" placeholder="Deskripsi / DESC2" value="${esc(value.description || "")}"><button type="button" class="remove-service" aria-label="Hapus layanan">×</button>`;
  row.querySelector(".remove-service").addEventListener("click", () => { row.remove(); markDirty(); });
  $("service-inputs").append(row);
}

function fillForm(data) {
  $("company").value = data.company || ""; $("witel").value = data.witel || "";
  if (data.sector) $("sector").value = data.sector;
  $("notes").value = data.notes || ""; $("service-inputs").replaceChildren();
  (data.services || []).forEach(addService);
}

function getInput() {
  return {company: $("company").value.trim(), sector: $("sector").value, witel: $("witel").value.trim(), notes: $("notes").value.trim(),
    services: [...document.querySelectorAll(".service-entry")].map(el => ({group4: el.querySelector(".service-g4").value.trim(), group5: el.querySelector(".service-g5").value.trim(), description: el.querySelector(".service-desc").value.trim()})).filter(s => s.group4 || s.group5 || s.description)};
}

async function api(path, data) {
  const response = await fetch(path, data === undefined ? {} : {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(data)});
  const body = await response.json();
  if (!response.ok) throw Error(typeof body.detail === "string" ? body.detail : "Periksa isian. Batas ukuran atau format data tidak sesuai.");
  return body;
}

async function checkRuntime() {
  try {
    const data = await api("/api/health"); const llm = data.llm;
    $("runtime-status").classList.toggle("ready", llm.ready);
    $("runtime-status").querySelector("span:nth-child(2)").textContent = llm.ready ? `${llm.model} · lokal` : "Model lokal belum siap";
    $("guide-runtime").textContent = `${llm.message}. Model yang dipilih: ${llm.model}. Riset: scraping Google, dengan Chromium bila perlu JavaScript. CAPTCHA menghentikan proses.`;
  } catch { $("runtime-status").querySelector("span:nth-child(2)").textContent = "Server belum terhubung"; $("guide-runtime").textContent = "Server aplikasi belum terhubung."; }
}

function existingFor(name) {
  if (!result) return [];
  const items = result.company.services.map(s => ({...s, label:s.group5 || s.group4}));
  const match = (s) => {
    const g = s.label.toLowerCase();
    if (["oca", "sms a2p"].includes(g)) return name === "Service" || name === "Marketing & Sales";
    if (["astinet", "vpn", "cloud", "collocation", "wifi", "nte", "rbt"].includes(g)) return name === "Tech Development";
    return false;
  };
  return [...new Set(items.filter(match).map(s => s.label))];
}

function renderDiagram() {
  if (!result) return;
  const a = result.analysis;
  const ecosystem = (name, key, cls) => `<section class="ecosystem-group ${cls}"><h3>${name}</h3><ul>${a.ecosystem[key].map((i,n) => `<li data-eco="${key}" data-eco-index="${n}" data-eco-name="${name}" role="button" tabindex="0" title="${esc(basisNames[i.basis])} · lihat bukti">${dot(i.basis)} ${esc(i.text)}</li>`).join("")}</ul></section>`;
  const cell = (activity, index, kind) => {
    const content = layer === "activity"
      ? activity.items.map(i => `<span class="activity-item">${dot(i.basis)}<span>${esc(i.text)}</span></span>`).join("")
      : existingFor(activity.name).map(s => `<span class="solution-item existing">${esc(s)} · Existing¹</span>`).join("") + a.opportunities.filter(o => o.activity === activity.name).map(o => (o.matched_products?.length ? o.matched_products : [{name:o.solution,status:"candidate_needs_validation"}]).map(p=>`<span class="solution-item">${esc(p.name)} · ${["existing_in_input","possible_existing_family"].includes(p.status) ? "Validasi existing¹" : "Kandidat²"}</span>`).join("")).join("");
    return `<button class="activity-cell" type="button" data-kind="${kind}" data-index="${index}" aria-label="Detail ${esc(activity.name)}"><span class="activity-title">${esc(activity.name)}</span><span class="activity-content">${content || '<span class="no-solution">Belum dipetakan.<br>Perlu discovery.</span>'}</span></button>`;
  };
  $("ivca-diagram").innerHTML = ecosystem("Complementary Institution", "complementary", "eco-complementary") + ecosystem("Supporting Industry", "supporting", "eco-supporting") + `<div class="core-activities"><div class="activities-row support-row">${a.support.map((v,i) => cell(v,i,"support")).join("")}</div><div class="activities-row primary-row">${a.primary.map((v,i) => cell(v,i,"primary")).join("")}</div></div><div class="margin-arrow"><span>Margin</span></div>` + ecosystem("Customer", "customers", "eco-customers") + ecosystem("Related Industry", "related", "eco-related");
  document.querySelectorAll(".activity-cell").forEach(b => b.addEventListener("click", () => showDetail(a[b.dataset.kind][Number(b.dataset.index)])));
  document.querySelectorAll("[data-eco]").forEach(el => { const open = () => showDetail({name:el.dataset.ecoName,items:[a.ecosystem[el.dataset.eco][Number(el.dataset.ecoIndex)]]}); el.addEventListener("click",open); el.addEventListener("keydown",e=>{if(["Enter"," "].includes(e.key)){e.preventDefault();open();}}); });
  $("activity-view").classList.toggle("active", layer === "activity"); $("solution-view").classList.toggle("active", layer === "solution");
  $("activity-view").setAttribute("aria-pressed", String(layer === "activity")); $("solution-view").setAttribute("aria-pressed", String(layer === "solution"));
  document.querySelector(".canvas-hint").textContent = layer === "activity" ? "Pilih aktivitas untuk melihat detail →" : "¹ Input pelanggan · ² Perlu validasi";
}

function insightDetail(item) {
  const refs = (item.source_ids || []).map(id => result.sources.find(s => s.id === id)).filter(Boolean);
  return `<div class="detail-insight"><span class="detail-basis">${dot(item.basis)}${esc(basisNames[item.basis])}</span><p>${esc(item.text)}</p>${item.evidence_quote ? `<blockquote>“${esc(item.evidence_quote)}”</blockquote>` : ""}${refs.map(s => `<a href="${esc(safeUrl(s.url))}" target="_blank" rel="noopener noreferrer">[${esc(s.id)}] ${esc(s.title)} →</a>`).join("")}</div>`;
}

function showDetail(activity) {
  $("detail-title").textContent = activity.name;
  const existing = existingFor(activity.name);
  const opportunities = result.analysis.opportunities.filter(o => o.activity === activity.name);
  $("detail-content").innerHTML = activity.items.map(insightDetail).join("") + (existing.length ? `<div class="detail-existing"><strong>Existing menurut data pelanggan</strong><br>${existing.map(esc).join(" · ")}<br>Pemetaan ke aktivitas ini adalah usulan berbasis kategori layanan. Kebutuhan, implementasi, dan kontrak aktif perlu dikonfirmasi.</div>` : "") + (opportunities.length ? `<h3 class="detail-heading">Peluang untuk divalidasi</h3>${opportunities.map(o => `<div class="detail-insight"><strong>${esc(o.solution)}</strong><p>${esc(o.rationale.text)}</p><div class="discovery-question">${esc(o.discovery_question)}</div></div>`).join("")}` : "");
  dialog("detail-dialog");
}

function opportunityMarkup(o) {
  const isExisting = result.company.services.some(s => (s.group5 || s.group4).toLowerCase() === o.solution.toLowerCase());
  return `<article class="opportunity-card"><div class="opportunity-header"><span class="opportunity-activity">${esc(o.activity)}</span><span class="prospect-badge">${isExisting ? "Validasi / ekspansi existing" : "Prospect · perlu validasi"}</span></div><h3>${esc(o.solution)}</h3><p>${esc(o.rationale.text)}</p><span class="detail-basis">${dot(o.rationale.basis)}${esc(basisNames[o.rationale.basis])}${o.rationale.source_ids.length ? " · " + o.rationale.source_ids.map(esc).join(", ") : ""}</span><div class="discovery-question">${esc(o.discovery_question)}</div><div class="product-matches">${(o.matched_products||[]).length ? '<span class="small-label">KANDIDAT DARI KATALOG RESMI</span>'+o.matched_products.map(p=>productMarkup(p,true)).join("") : '<p class="no-product-match">Belum ada kandidat produk resmi yang cocok dari katalog yang tersedia. Buka tab Katalog resmi untuk memperbarui sumber.</p>'}</div></article>`;
}

function productMarkup(p, matched=false) {
  return `<article class="product-card"><span class="source-tag">${esc(new URL(safeUrl(p.source_url),window.location.href).hostname)} · ${["structured_product","official_product_payload"].includes(p.entry_type) ? "Produk/layanan" : "Halaman solusi"}</span><h3>${esc(p.name)}</h3>${p.availability === "maintenance" ? '<p class="product-status">Halaman pemeliharaan — tidak masuk rekomendasi otomatis</p>' : p.availability === "coming_soon" ? '<p class="product-status">Coming soon — tidak masuk rekomendasi otomatis</p>' : ""}<p>${esc(p.description.slice(0,350))}${p.description.length>350?"…":""}</p>${matched?`<p class="product-status">${p.status === "existing_in_input" ? "Existing menurut input — validasi implementasi / ekspansi" : p.status === "possible_existing_family" ? "Kemungkinan satu keluarga existing — konfirmasi produk dan paket" : "Kandidat — kebutuhan belum dikonfirmasi"}</p><p class="source-meta">${p.match_method === "model_selected" ? "ID dipilih LLM lokal" : "Pencocokan kata kunci"}${p.matched_terms?.length ? " · Istilah terkait: "+p.matched_terms.map(esc).join(", ") : ""}</p>`:""}<a href="${esc(safeUrl(p.source_url))}" target="_blank" rel="noopener noreferrer">Lihat halaman resmi →</a><p class="source-meta">Dibaca ${esc(new Date(p.observed_at).toLocaleString("id-ID",{timeZone:"Asia/Jakarta"}))} WIB</p><details><summary class="text-button">Kutipan katalog</summary><blockquote>${esc(p.evidence_quote)}</blockquote></details></article>`;
}

function renderCatalog(catalog) {
  currentCatalog=catalog||currentCatalog;
  $("catalog-count").textContent=(currentCatalog.products||[]).length;
  $("catalog-status").textContent=currentCatalog.notice || "Katalog belum dibaca.";
  $("catalog-list").innerHTML=(currentCatalog.products||[]).map(p=>productMarkup(p)).join("") || `<div class="empty-state"><h3>Belum ada produk resmi yang terbaca.</h3><p>Tidak ada produk yang diklaim terverifikasi. Klik Perbarui katalog resmi saat situs dapat diakses.</p></div>`;
  if(currentCatalog.errors?.length)$("catalog-list").innerHTML+=`<div class="source-card"><h3>Sumber yang belum terbaca</h3>${currentCatalog.errors.map(e=>`<p>${esc(e.url)}<br>${esc(e.message)}</p>`).join("")}</div>`;
}

async function refreshCatalog() {
  const button=$("refresh-catalog");button.disabled=true;button.textContent="Membaca situs resmi…";
  try {
    const catalog=await api("/api/catalog/refresh",{});renderCatalog(catalog);
    if(result){
      const analysis=structuredClone(result.analysis);
      analysis.opportunities=analysis.opportunities.map(o=>({activity:o.activity,solution:o.solution,rationale:o.rationale,discovery_question:o.discovery_question,product_ids:o.product_ids||[]}));
      const data=await api("/api/match",{company:result.company,analysis});
      const wasDirty=dirty;renderResult({...result,analysis:data.analysis,catalog:data.catalog});if(wasDirty)markDirty();
    }
    toast(catalog.products.length?"Katalog dan kandidat produk diperbarui. Tinjau kecocokannya.":"Katalog belum terbaca. Lihat status akses sumber.");
  }catch(e){$("catalog-status").textContent=e.message;}
  finally{button.disabled=false;button.textContent="Perbarui katalog resmi";}
}

function renderResult(data) {
  result = data; dirty = false; $("dirty-banner").hidden = true;
  const c = data.company, a = data.analysis, live = data.mode === "live";
  $("result-company").textContent = c.company; $("company-sector").textContent = sectors[c.sector] || c.sector;
  $("company-avatar").textContent = c.company.split(/\s+/).filter(v => !["PT","CV"].includes(v.toUpperCase())).slice(0,2).map(v => v[0]).join("");
  $("result-witel").textContent = c.witel || "Wilayah belum diisi";
  $("analysis-kind").textContent = live ? "ANALISIS LLM LOKAL" : "KERANGKA · BELUM DIRISET";
  $("result-indicator").innerHTML = `<span></span> ${live ? "Analisis tersusun" : "Contoh kerangka"}`;
  $("overview").textContent = a.overview.text;
  $("opportunity-count").textContent = a.opportunities.length; $("source-count").textContent = data.sources.length;
  $("existing-services").innerHTML = [...new Set(c.services.map(s => s.group5 || s.group4))].map(s => `<span class="chip">${esc(s)}</span>`).join("") || '<span class="chip">Belum diisi</span>';
  $("opportunities-list").innerHTML = a.opportunities.map(opportunityMarkup).join("");
  $("sources-list").innerHTML = data.sources.length ? `<div class="source-card"><span class="small-label">QUERY GOOGLE</span><p>${esc(data.query)}</p><p>Hanya nama dan segmen yang dikirim ke Google. Data layanan dan catatan kunjungan diproses lokal.</p></div>` + data.sources.map(s => `<article class="source-card"><span class="source-tag">${esc(s.id)} · ${s.kind === "page" ? "Halaman publik" : "Cuplikan Google"}</span><h3>${esc(s.title)}</h3><a href="${esc(safeUrl(s.url))}" target="_blank" rel="noopener noreferrer">${esc(s.url)} →</a><p>${esc(s.snippet)}</p><p class="source-meta">${esc(s.fetch_status)} · ${esc(new Date(s.retrieved_at).toLocaleString("id-ID", {timeZone:"Asia/Jakarta"}))} WIB</p><details><summary class="text-button">Teks yang dibaca model</summary><p>${esc(s.text)}</p></details></article>`).join("") : `<div class="empty-state"><h3>Belum ada riset publik.</h3><p>Canvas ini memakai contoh kerangka sektor.<br>Jalankan “Riset & buat analisis” untuk menambahkan sumber Google dan analisis model lokal.</p></div>`;
  $("data-table").innerHTML = c.services.map(s => `<tr><td>${esc(s.group4)}</td><td>${esc(s.group5)}</td><td>${esc(s.description || "—")}</td></tr>`).join("") || '<tr><td colspan="3">Belum ada layanan pada input.</td></tr>';
  $("customer-notes").textContent = c.notes ? "Catatan input: " + c.notes : "Tidak ada catatan tambahan dari pelanggan.";
  $("result-disclaimer").innerHTML = `${!live ? "<strong>CONTOH, BUKAN HASIL RISET.</strong> " : "<strong>PERLU TINJAUAN MANUSIA.</strong> "}${data.warnings.map(esc).join(" ")}`;
  renderDiagram();
  renderCatalog(data.catalog);
}

function setTab(name) {
  activeTab = name;
  document.querySelectorAll("[data-tab]").forEach(b => { b.setAttribute("aria-selected", String(b.dataset.tab === name)); b.tabIndex = b.dataset.tab === name ? 0 : -1; });
  ["canvas","opportunities","sources","catalog"].forEach(t => $("tab-"+t).hidden = t !== name);
}

async function preview() {
  if (!$("company-form").reportValidity()) return;
  const version = ++previewVersion, snapshot = getInput();
  try { $("preview-button").disabled = true; const output = await api("/api/preview", snapshot); if(version !== previewVersion)return; renderResult(output); if(JSON.stringify(snapshot)!==JSON.stringify(getInput()))markDirty(); $("error-card").hidden = true; }
  catch (e) { if(version === previewVersion)showError(e.message); } finally { if(version === previewVersion)$("preview-button").disabled = false; }
}

function busy(value) {
  $("company-form").querySelectorAll("input, select, textarea, button").forEach(el => el.disabled = value);
  $("progress").hidden = !value;
  $("analyze-button").firstElementChild.textContent = value ? "Analisis berjalan…" : "Riset & buat analisis";
}

async function analyze(event) {
  event.preventDefault(); if (!$("company-form").reportValidity()) return;
  controller = new AbortController(); const snapshot = getInput(); let completed = false;
  busy(true); $("error-card").hidden = true; $("progress-title").textContent = "Memeriksa model lokal…";
  try {
    const response = await fetch("/api/analyze", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(snapshot), signal:controller.signal});
    if (!response.ok) { const body = await response.json(); throw Error(typeof body.detail === "string" ? body.detail : "Data input belum valid."); }
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = "";
    const processEvent = line => {
      if (!line.trim()) return;
      const e = JSON.parse(line);
      if (e.type === "progress") $("progress-title").textContent = e.message;
      if (e.type === "research") $("progress-detail").textContent = `${e.sources.length} sumber ditemukan. Memproses dengan model lokal…`;
      if (e.type === "result") { renderResult(e.data); completed = true; setTab("canvas"); toast("Analisis selesai. Tinjau sumber dan validasi hipotesisnya."); }
      if (e.type === "error") throw Error(e.message);
    };
    while (true) { const {done, value} = await reader.read(); if (done) break; buffer += decoder.decode(value, {stream:true}); const lines = buffer.split("\n"); buffer = lines.pop(); lines.forEach(processEvent); }
    buffer += decoder.decode(); if (buffer.trim()) processEvent(buffer);
    if (!completed) throw Error("Koneksi berakhir sebelum analisis selesai. Canvas sebelumnya tetap ditampilkan.");
  } catch (e) {
    if (e.name === "AbortError") toast("Analisis dibatalkan. Canvas sebelumnya tetap ditampilkan."); else showError(e.message);
    controller?.abort();
  } finally { controller = null; busy(false); checkRuntime(); }
}

function download(content, mime, extension) {
  const blob = new Blob([content], {type:mime}); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url;
  a.download = `IVCA-${result.company.company.replace(/[^a-zA-Z0-9-]/g,"-")}-${result.mode}.${extension}`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  if (dirty) toast("Ekspor memakai data canvas sebelumnya. Input baru belum dianalisis.");
}

function exportCSV() {
  const cell = value => { let text = String(value ?? ""); if (/^[\s]*[=+\-@\t\r]/.test(text)) text = "'" + text; return '"' + text.replaceAll('"', '""') + '"'; };
  const rows = [["Perusahaan","Mode","Aktivitas","Solusi","Status","Alasan","Dasar","Sumber","Pertanyaan discovery","Kandidat produk resmi","URL produk","Status produk"]];
  result.analysis.opportunities.forEach(o => rows.push([result.company.company,result.mode,o.activity,o.solution,"Hipotesis / perlu validasi",o.rationale.text,basisNames[o.rationale.basis],o.rationale.source_ids.join("; "),o.discovery_question,(o.matched_products||[]).map(p=>p.name).join("; "),(o.matched_products||[]).map(p=>p.source_url).join("; "),(o.matched_products||[]).map(p=>p.status).join("; ")]));
  download("\ufeff"+rows.map(r => r.map(cell).join(",")).join("\r\n"), "text/csv;charset=utf-8", "csv");
}

function exportSVG() {
  const previous = activeTab; setTab("canvas");
  const root = $("ivca-diagram"), base = root.getBoundingClientRect(); const pad = 28, top = 112;
  const width = Math.ceil(base.width + pad*2), height = Math.ceil(base.height + top + 100);
  const parts = [`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><rect width="100%" height="100%" fill="#ffffff"/><style>text{font-family:Arial,sans-serif}</style>`];
  const ctx = document.createElement("canvas").getContext("2d");
  const text = (value,x,y,maxWidth,size=10,color="#54684c",weight="normal",maxLines=12) => {
    ctx.font = `${weight} ${size}px Arial`; const words = String(value).split(/\s+/), lines = []; let line="";
    for (const word of words) { const next = line ? line+" "+word : word; if (ctx.measureText(next).width > maxWidth && line) { lines.push(line); line=word; } else line=next; } if (line) lines.push(line);
    lines.slice(0,maxLines).forEach((l,i) => parts.push(`<text x="${x}" y="${y+i*size*1.45}" font-size="${size}" fill="${color}" font-weight="${weight}">${esc(l)}</text>`));
  };
  const box = el => { const r=el.getBoundingClientRect(); return {x:r.x-base.x+pad,y:r.y-base.y+top,w:r.width,h:r.height}; };
  text(result.company.company,pad,34,width-pad*2,21,"#1d3434","bold");
  text(`${sectors[result.company.sector]} · ${result.company.witel || "Wilayah belum diisi"}`,pad,57,width-pad*2,11);
  text(`${result.mode === "live" ? "ANALISIS LLM LOKAL" : "CONTOH KERANGKA — BELUM DIRISET"} · ${layer === "activity" ? "Aktivitas bisnis" : "Pemetaan solusi"} · ${new Date(result.generated_at).toLocaleString("id-ID",{timeZone:"Asia/Jakarta"})} WIB`,pad,78,width-pad*2,9,"#9a8656");
  for (const el of root.querySelectorAll(".ecosystem-group,.activity-cell")) {
    const b=box(el); parts.push(`<rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" rx="4" fill="white" stroke="#d4e1ce"/>`);
    const title=el.querySelector("h3,.activity-title"), t=box(title); const primary=!!el.closest(".primary-row");
    parts.push(`<rect x="${t.x}" y="${t.y}" width="${t.w}" height="${t.h}" fill="${primary ? "#2a7d6b" : "#edf3e7"}"/>`);
    text(title.textContent,t.x+5,t.y+13,t.w-10,8,primary ? "white" : "#536f48","bold",3);
    if (el.classList.contains("ecosystem-group")) {
      for (const li of el.querySelectorAll("li")) { const l=box(li); text(li.textContent,l.x+5,l.y+13,l.w-10,8,"#74846a","normal",6); }
    } else {
      for (const item of el.querySelectorAll(".activity-item,.solution-item,.no-solution")) {
        const r=box(item); const i=item.querySelector(".basis-dot");
        if (i) parts.push(`<circle cx="${r.x+2}" cy="${r.y+6}" r="2" fill="${getComputedStyle(i).backgroundColor}"/>`);
        text(item.textContent,r.x+(i?8:1),r.y+10,r.w-(i?8:2),8,"#74846a","normal",8);
      }
    }
  }
  const m=box(root.querySelector(".margin-arrow")); parts.push(`<polygon points="${m.x},${m.y} ${m.x+m.w*.55},${m.y} ${m.x+m.w},${m.y+m.h/2} ${m.x+m.w*.55},${m.y+m.h} ${m.x},${m.y+m.h}" fill="#dde9d5"/><text transform="translate(${m.x+12} ${m.y+m.h/2+25}) rotate(-90)" font-size="9" fill="#6f8a5e">MARGIN</text>`);
  text("Hijau: data pelanggan · Biru: sumber publik · Emas: hipotesis",pad,top+base.height+25,width-pad*2,9);
  text("Existing = input pelanggan, kontrak belum diverifikasi. Prospect = usulan untuk divalidasi. Pemetaan solusi perlu konfirmasi.",pad,top+base.height+44,width-pad*2,9,"#8e967f");
  text(`Kerangka: ToT SME Assistant IVCA hlm. 10, 35–36 · ${result.sources.length} sumber · ${result.model || "Tanpa LLM"} · Detail bukti tersedia pada ekspor JSON.`,pad,top+base.height+63,width-pad*2,8,"#8e967f");
  parts.push("</svg>"); download(parts.join(""),"image/svg+xml;charset=utf-8","svg"); setTab(previous);
}

async function parseImport() {
  $("import-error").textContent="";
  try {
    const data = await api("/api/import",{text:$("import-text").value}); imported=data.companies;
    $("import-company-select").innerHTML=imported.map((c,i)=>`<option value="${i}">${esc(c.company)} · ${c.services.length} baris layanan</option>`).join("");
    $("import-company-choice").hidden=false; $("apply-import").hidden=false; $("parse-import").hidden=true;
  } catch(e) { $("import-error").textContent=e.message; }
}

function bind() {
  $("preset").addEventListener("change", () => { const data=examples.find(c=>c.id===$("preset").value); if(data) {fillForm(data);markDirty();preview();} else {++previewVersion;fillForm({sector:$("sector").value});$("preview-button").disabled=false;markDirty();$("company").focus();} });
  $("company-form").addEventListener("input",markDirty); $("company-form").addEventListener("change",markDirty);
  $("add-service").addEventListener("click", () => { if(document.querySelectorAll(".service-entry").length>=80) return toast("Maksimal 80 baris layanan.");addService();markDirty(); });
  $("preview-button").addEventListener("click",preview); $("company-form").addEventListener("submit",analyze);
  $("cancel-analysis").addEventListener("click",()=>controller?.abort());
  $("close-error").addEventListener("click",()=>$("error-card").hidden=true);
  $("activity-view").addEventListener("click",()=>{layer="activity";renderDiagram();}); $("solution-view").addEventListener("click",()=>{layer="solution";renderDiagram();});
  document.querySelectorAll("[data-tab]").forEach(b=>{b.addEventListener("click",()=>setTab(b.dataset.tab));b.addEventListener("keydown",e=>{if(!["ArrowLeft","ArrowRight","Home","End"].includes(e.key))return;e.preventDefault();const tabs=["canvas","opportunities","sources","catalog"];let index=tabs.indexOf(activeTab);index=e.key==="Home"?0:e.key==="End"?3:(index+(e.key==="ArrowRight"?1:3))%4;setTab(tabs[index]);document.querySelector(`[data-tab="${tabs[index]}"]`).focus();});});
  ["guide-nav","runtime-status","error-guide"].forEach(id=>$(id).addEventListener("click",()=>dialog("guide-dialog")));
  $("workspace-nav").addEventListener("click",()=>document.querySelector(".workspace").scrollIntoView({behavior:"smooth"}));
  $("refresh-status").addEventListener("click",checkRuntime);
  $("refresh-catalog").addEventListener("click",refreshCatalog);
  document.querySelectorAll("[data-close]").forEach(b=>b.addEventListener("click",()=>$(b.dataset.close).close()));
  document.querySelectorAll("dialog").forEach(d=>d.addEventListener("click",e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();}}));
  $("open-import").addEventListener("click",()=>dialog("import-dialog")); $("parse-import").addEventListener("click",parseImport);
  $("import-text").addEventListener("input",()=>{$("parse-import").hidden=false;$("apply-import").hidden=true;$("import-company-choice").hidden=true;});
  $("import-file").addEventListener("change",async e=>{const f=e.target.files[0];if(!f)return;if(f.size>150000){$("import-error").textContent="Maksimal ukuran 150 KB.";return;}$("import-text").value=await f.text();$("parse-import").hidden=false;$("apply-import").hidden=true;$("import-company-choice").hidden=true;});
  $("apply-import").addEventListener("click",()=>{const c=imported[Number($("import-company-select").value)];fillForm({...c,sector:$("sector").value,notes:"Diimpor dari tabel pelanggan. Konfirmasi segmen dan status layanan sebelum analisis."});$("preset").value="custom";markDirty();$("import-dialog").close();toast("Tabel diimpor. Periksa segmen bisnis, lalu jalankan analisis.");});
  $("export-button").addEventListener("click",()=>{if(!result)return;$("export-menu").hidden=!$("export-menu").hidden;$("export-button").setAttribute("aria-expanded",String(!$("export-menu").hidden));});
  document.addEventListener("click",e=>{if(!e.target.closest(".export-wrap")){$("export-menu").hidden=true;$("export-button").setAttribute("aria-expanded","false");}});
  $("export-json").addEventListener("click",()=>download(JSON.stringify(result,null,2),"application/json","json")); $("export-csv").addEventListener("click",exportCSV);$("export-svg").addEventListener("click",exportSVG);$("export-print").addEventListener("click",()=>window.print());
  document.querySelectorAll(".export-menu button").forEach(b=>b.addEventListener("click",()=>{$("export-menu").hidden=true;$("export-button").setAttribute("aria-expanded","false");}));
}

async function init() {
  bind(); checkRuntime();
  try { const data=await api("/api/examples"); examples=data.companies;sectors=data.sectors;
    $("preset").innerHTML=examples.map(c=>`<option value="${esc(c.id)}">${esc(c.company)}</option>`).join("")+'<option value="custom">Perusahaan lain / input sendiri</option>';
    fillForm(examples[0]); await preview();setTab("canvas");
  } catch(e) { showError("Gagal memuat aplikasi: "+e.message); }
}
init();
