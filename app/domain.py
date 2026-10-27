"""Input pelanggan dan kerangka IVCA. Contoh adalah hipotesis, bukan hasil riset."""
import csv
import io
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SECTORS = {
    "retail": "IndiBiz Ruko",
    "cooperative": "IndiBiz Finance · Koperasi",
    "bank": "IndiBiz Finance · BPR",
    "health": "IndiBiz Health",
    "education": "IndiBiz Education",
}
SUPPORT = ["Firm Infrastructure", "HR Management", "Tech Development", "Procurement"]
PRIMARY = ["Inbound Logistics", "Operations", "Outbound Logistics", "Marketing & Sales", "Service"]


class Service(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group4: str = Field(max_length=120)
    group5: str = Field(max_length=120)
    description: str = Field(default="", max_length=500)


class AnalysisInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    company: str = Field(min_length=2, max_length=180)
    sector: Literal["retail", "cooperative", "bank", "health", "education"]
    witel: str = Field(default="", max_length=180)
    services: list[Service] = Field(default_factory=list, max_length=80)
    notes: str = Field(default="", max_length=6000)


class Insight(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=250)
    basis: Literal["customer", "public", "hypothesis"]
    source_ids: list[str] = Field(default_factory=list, max_length=8)
    evidence_quote: str = Field(default="", max_length=600)


class Activity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    items: list[Insight] = Field(min_length=1, max_length=3)


class Ecosystem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supporting: list[Insight] = Field(min_length=1, max_length=5)
    complementary: list[Insight] = Field(min_length=1, max_length=5)
    related: list[Insight] = Field(min_length=1, max_length=5)
    customers: list[Insight] = Field(min_length=1, max_length=5)


class Opportunity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    activity: str
    solution: str = Field(min_length=1, max_length=100)
    rationale: Insight
    discovery_question: str = Field(min_length=1, max_length=350)
    product_ids: list[str] = Field(default_factory=list, max_length=3)


class ModelAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    overview: Insight
    support: list[Activity] = Field(min_length=4, max_length=4)
    primary: list[Activity] = Field(min_length=5, max_length=5)
    ecosystem: Ecosystem
    opportunities: list[Opportunity] = Field(min_length=1, max_length=8)


def service(a, b=None, d=""):
    return {"group4": a, "group5": b or a, "description": d}


EXAMPLES = [
    {"id": "sidogiri", "company": "KOPONTRES SIDOGIRI", "sector": "retail", "witel": "Telkom JATIM TIMUR",
     "notes": "Contoh retail Basmallah sesuai arahan pengguna. Nama STANDARD_NAME pada gambar: KOPONTRES SIDOGIRI. Hubungan badan usaha dengan brand serta ejaan nama perlu dikonfirmasi.",
     "services": [service("ASTINet", d="Pend Abonemen ASTINet Dedicated"), service("RBT", d="Pendapatan Anti Virus"), service("SMS A2P", d="Potongan Pendapatan Anti virus")]},
    {"id": "unsiq", "company": "UNSIQ WONOSOBO", "sector": "education", "witel": "Telkom YOGYA JATENG SELATAN", "notes": "Nama dan layanan ditranskripsikan dari gambar pengguna. Baris revenue recognition adalah keterangan akuntansi, bukan layanan tambahan.",
     "services": [service("ASTINet", d="Kriteria KB; Pend Abonemen ASTINet Dedicated; Revenue Recognition; Reverse Revenue Recognition"), service("Cloud", d="Pend PlasaTron (Collocation) IDC"), service("Collocation", d="Revenue Recognition; Reverse Revenue Recognition"), service("Inkubasi", d="Revenue Recognition; Reverse Revenue Recognition"), service("Inkubasi", "OCA", "Pend Produk & Solusi Digital"), service("Others", d="Revenue Recognition; Reverse Revenue Recognition"), service("Wifi", d="Pendapatan Wifi Managed Service; Revenue Recognition; Reverse Revenue Recognition")]},
    {"id": "ashavin", "company": "PT ASHAVIN PANDAWA MEDIKA INDONESIA", "sector": "health", "witel": "Telkom SOLO JATENG TIMUR", "notes": "Segmen rumah sakit mengikuti arahan pengguna; identitas fasilitas dan profil badan usaha perlu dikonfirmasi melalui sumber publik.",
     "services": [service("ASTINet", d="Pend Abonemen ASTINet Dedicated"), service("NTE", d="Pendapatan Manage Platform")]},
    {"id": "surya", "company": "BPR BANK SURYA YUDHA", "sector": "bank", "witel": "Telkom YOGYA JATENG SELATAN", "notes": "Data layanan existing berasal dari gambar pengguna; status kontrak aktif belum diverifikasi.",
     "services": [service("ASTINet", d="Pend Abonemen ASTINet Dedicated"), service("Inkubasi", "OCA", "Pend Produk & Solusi Digital"), service("VPN", d="Pend Abonemen TelkomNet VPN Intranet")]},
    {"id": "kospin", "company": "KOSPIN JASA", "sector": "cooperative", "witel": "Telkom SEMARANG JATENG UTARA", "notes": "Data layanan existing berasal dari gambar pengguna; status kontrak aktif belum diverifikasi.",
     "services": [service("ASTINet", d="Pend Abonemen ASTINet Dedicated"), service("VPN", d="Pend Abonemen TelkomNet VPN Intranet")]},
]

TEMPLATES = {
    "retail": {
        "supporting": ["Distributor barang konsumsi", "Pemasok produk lokal", "Penyedia perangkat kasir"],
        "complementary": ["Dinas perdagangan", "Komunitas UMKM", "Lembaga sertifikasi halal"],
        "related": ["Perbankan & pembayaran", "Logistik", "Pemasaran digital"], "customers": ["Pembeli rumah tangga", "Anggota komunitas", "Pelanggan gerai"],
        "primary": [["Penerimaan barang pemasok", "Pencatatan stok masuk"], ["Operasional gerai & kasir", "Kontrol persediaan"], ["Penyerahan barang belanja", "Distribusi antargerai"], ["Promosi produk & gerai", "Program loyalitas"], ["Penanganan keluhan", "Retur & layanan anggota"]],
    },
    "education": {
        "supporting": ["Sekolah asal mahasiswa", "Penerbit & penyedia laboratorium", "Penyedia teknologi"], "complementary": ["Kementerian pendidikan terkait", "Lembaga akreditasi", "Asosiasi perguruan tinggi"],
        "related": ["Dunia industri", "Lembaga riset", "Perbankan"], "customers": ["Mahasiswa", "Orang tua", "Mitra industri"],
        "primary": [["Penerimaan mahasiswa baru", "Persiapan kurikulum"], ["Perkuliahan & penelitian", "Administrasi akademik"], ["Kelulusan & sertifikasi", "Diseminasi hasil riset"], ["Promosi penerimaan", "Kemitraan akademik"], ["Layanan mahasiswa", "Karier & jejaring alumni"]],
    },
    "health": {
        "supporting": ["Distributor obat", "Pemasok alat kesehatan", "Laboratorium mitra"], "complementary": ["Kementerian Kesehatan", "Dinas kesehatan", "Lembaga akreditasi"],
        "related": ["Asuransi & penjamin", "Farmasi", "Layanan rujukan"], "customers": ["Pasien", "Keluarga pasien", "Mitra penjamin"],
        "primary": [["Pendaftaran & rujukan", "Ketersediaan obat & alat"], ["Pemeriksaan & tindakan", "Pengelolaan rekam medis"], ["Pemulangan & rujukan lanjut", "Penagihan layanan"], ["Edukasi kesehatan", "Kemitraan penjamin"], ["Tindak lanjut pasien", "Penanganan keluhan"]],
    },
    "bank": {
        "supporting": ["Penyedia core banking", "Penyedia infrastruktur TI", "Mitra pembayaran"], "complementary": ["OJK", "Bank Indonesia", "Lembaga penjamin simpanan"],
        "related": ["Bank umum", "Koperasi", "Perusahaan teknologi keuangan"], "customers": ["Nasabah individu", "Pelaku UMKM", "Nasabah badan usaha"],
        "primary": [["Penghimpunan dana", "Verifikasi data nasabah"], ["Analisis & administrasi kredit", "Operasional cabang"], ["Pencairan kredit", "Pemrosesan pembayaran"], ["Promosi produk simpanan", "Akuisisi & retensi nasabah"], ["Layanan nasabah", "Penanganan pengaduan"]],
    },
    "cooperative": {
        "supporting": ["Anggota penyimpan dana", "Mitra perbankan", "Penyedia sistem koperasi"], "complementary": ["Kementerian koperasi", "Dinas koperasi", "Asosiasi koperasi"],
        "related": ["Pelaku UMKM", "Bank mitra", "Penyedia pembayaran"], "customers": ["Anggota koperasi", "Anggota pelaku UMKM", "Calon anggota"],
        "primary": [["Pendaftaran anggota", "Penghimpunan simpanan"], ["Analisis pinjaman", "Administrasi simpan pinjam"], ["Pencairan pinjaman", "Pencatatan angsuran"], ["Edukasi produk koperasi", "Pengembangan keanggotaan"], ["Layanan anggota", "Pengaduan & pendampingan"]],
    },
}


def sample_analysis(data: AnalysisInput):
    t = TEMPLATES[data.sector]
    def item(text):
        return {"text": text, "basis": "hypothesis", "source_ids": []}
    support_items = [["Perencanaan & keuangan", "Tata kelola & kepatuhan"], ["Rekrutmen & pelatihan", "Pengelolaan kinerja"], ["Pengelolaan aplikasi & data", "Keamanan & jaringan"], ["Seleksi vendor", "Pembelian & kontrak"]]
    return ModelAnalysis(
        overview=item("Kerangka awal sektor untuk mempersiapkan discovery. Aktivitas dan peluang ini belum merupakan fakta spesifik perusahaan."),
        support=[Activity(name=n, items=[item(v) for v in vs]) for n, vs in zip(SUPPORT, support_items)],
        primary=[Activity(name=n, items=[item(v) for v in vs]) for n, vs in zip(PRIMARY, t["primary"])],
        ecosystem=Ecosystem(**{k: [item(v) for v in t[k]] for k in ["supporting", "complementary", "related", "customers"]}),
        opportunities=[Opportunity(activity="Tech Development", solution="Monitoring jaringan", rationale=item("Visibilitas jaringan dapat membantu operasional; kebutuhan dan perangkat existing harus dikonfirmasi."), discovery_question="Bagaimana tim memantau gangguan jaringan dan berapa lama pemulihannya?"), Opportunity(activity="Service", solution="Komunikasi pelanggan", rationale=item("Kanal layanan terpusat berpotensi membantu tindak lanjut pelanggan; validasi proses saat ini terlebih dahulu."), discovery_question="Kanal apa yang digunakan pelanggan dan bagaimana keluhan ditindaklanjuti?")],
    )


def parse_table(raw: str, company: str = "") -> dict:
    """Excel pivot: carry forward company/witel/group4/group5, never DESC2."""
    if len(raw) > 150_000:
        raise ValueError("Data terlalu besar. Batasi sampai 150 KB.")
    lines = raw.lstrip("\ufeff").strip()
    if not lines:
        raise ValueError("Tempel tabel dengan header STANDARD_NAME, WITEL_HO, GROUP4, GROUP5, DESC2.")
    delimiter = "\t" if "\t" in lines.splitlines()[0] else (";" if ";" in lines.splitlines()[0] else ",")
    reader = csv.DictReader(io.StringIO(lines), delimiter=delimiter)
    headers = {h.strip().upper(): h for h in (reader.fieldnames or []) if h}
    required = ["STANDARD_NAME", "WITEL_HO", "GROUP4", "GROUP5", "DESC2"]
    if any(h not in headers for h in required):
        raise ValueError("Header wajib: " + ", ".join(required))
    companies = {}
    state = {k: "" for k in required}
    for index, row in enumerate(reader):
        if index >= 1000:
            raise ValueError("Maksimal 1.000 baris per impor.")
        vals = {k: (row.get(headers[k]) or "").strip() for k in required}
        if vals["STANDARD_NAME"] and vals["STANDARD_NAME"] != state["STANDARD_NAME"]:
            state = {k: "" for k in required}
        # A new parent group must not inherit the previous child group.
        if vals["GROUP4"] and vals["GROUP4"] != state["GROUP4"]:
            state["GROUP5"] = ""
        for k in required[:-1]:
            if vals[k]:
                state[k] = vals[k]
        name = state["STANDARD_NAME"]
        if not name:
            continue
        entry = companies.setdefault(name, {"company": name, "witel": state["WITEL_HO"], "services": []})
        entry["witel"] = state["WITEL_HO"]
        if state["GROUP4"] or state["GROUP5"]:
            s = service(state["GROUP4"], state["GROUP5"] or state["GROUP4"], vals["DESC2"])
            # Validate field lengths before returning to the browser.
            Service.model_validate(s)
            if s not in entry["services"]:
                entry["services"].append(s)
    matches = [v for k, v in companies.items() if not company or k.casefold() == company.casefold().strip()]
    if not matches:
        raise ValueError("Perusahaan tidak ditemukan pada tabel.")
    return {"companies": matches}
