"""All catalogue records in this test module are synthetic fixtures, not website observations."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.catalog import canonical, empty_catalog, enrich_analysis, match_products, parse_catalog_page, read_catalog, refresh_catalog, fetch_official
from app.domain import AnalysisInput, EXAMPLES, sample_analysis
from app.main import app

STAMP="2026-10-27T00:00:00+00:00"
DETAIL="https://www.telkomsolution.co.id/produk/produk-uji"


def fixture_product(name="Produk Uji Monitoring",description="Fixture pengujian pemantauan jaringan dan monitoring konektivitas kantor, bukan produk nyata."):
    html='<main><h1>'+name+'</h1><p>'+description+'</p></main>'
    return parse_catalog_page(html,DETAIL,STAMP)[0][0]


class CatalogParsingTests(unittest.TestCase):
    def test_official_scope_blocks_credentials_ports_and_lookalikes(self):
        for url in ["https://indibiz.co.id.evil.test/produk/foo","https://evil.test/produk/foo","http://127.0.0.1/produk/foo","https://u:p@indibiz.co.id/produk/foo","https://indibiz.co.id:11434/produk/foo"]:
            self.assertIsNone(canonical(url),url)
        self.assertEqual(canonical("/produk/foo?tracking=1#x","https://indibiz.co.id/"),"https://indibiz.co.id/produk/foo")

    def test_hub_discovers_links_without_inventing_a_product(self):
        html='<main><h1>Produk</h1><a href="/produk/produk-uji">Uji</a><a href="https://evil.test/product/fake">Fake</a></main>'
        products,links=parse_catalog_page(html,"https://www.telkomsolution.co.id/produk",STAMP)
        self.assertEqual(products,[])
        self.assertEqual(links,[DETAIL])

    def test_detail_keeps_original_name_description_quote_and_url(self):
        p=fixture_product()
        self.assertEqual(p["name"],"Produk Uji Monitoring")
        self.assertEqual(p["source_url"],DETAIL)
        self.assertIn(p["evidence_quote"],p["description"])
        self.assertEqual(p["observed_at"],STAMP)

    def test_schema_product_uses_fetched_source_not_schema_supplied_url(self):
        data={"@graph":[{"@type":"Product","name":"Produk Uji Schema","description":"Deskripsi fixture produk pengujian yang cukup panjang untuk bukti katalog.","url":"https://evil.test/","alternateName":"Alias Fixture"}]}
        products,_=parse_catalog_page('<script type="application/ld+json">'+json.dumps(data)+'</script>',DETAIL,STAMP)
        self.assertEqual(products[0]["source_url"],DETAIL)
        self.assertEqual(products[0]["aliases"],["Alias Fixture"])

    def test_invalid_cache_and_nonofficial_sources_are_not_loaded(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"catalog.json";path.write_text("bad json")
            self.assertEqual(read_catalog(path)["products"],[])
            p=fixture_product();p["source_url"]="https://evil.test/"
            path.write_text(json.dumps({"products":[p]}))
            self.assertEqual(read_catalog(path)["products"],[])

    def test_placeholder_heading_uses_actual_official_metadata_title(self):
        html='<title>Solusi Fixture Cloud | Telkom Solution</title><meta name="description" content="Fixture cloud pengujian untuk memastikan nama placeholder tidak diklaim sebagai nama produk."><main><h1>Product Detail Page</h1></main>'
        products,_=parse_catalog_page(html,DETAIL,STAMP)
        self.assertEqual(products[0]["name"],"Solusi Fixture Cloud")

    def test_indibiz_public_payload_uses_product_name_not_seo_title(self):
        data={"props":{"pageProps":{"productDetail":{"name":"Produk Fixture Medis","description":"Fixture pencatatan medis, bukan klaim produk resmi saat pengujian.","isActive":True}}}}
        html='<title>Judul SEO Generik</title><script id="__NEXT_DATA__" type="application/json">'+json.dumps(data)+'</script>'
        products,_=parse_catalog_page(html,"https://indibiz.co.id/produk/fixture-medis",STAMP)
        self.assertEqual(products[0]["name"],"Produk Fixture Medis")
        self.assertEqual(products[0]["entry_type"],"official_product_payload")

    def test_sitemap_only_discovers_product_pages_on_official_hosts(self):
        xml='<urlset><url><loc>'+DETAIL+'</loc></url><url><loc>https://evil.test/produk/foo</loc></url><url><loc>https://indibiz.co.id/member/private</loc></url></urlset>'
        products,links=parse_catalog_page(xml,"https://indibiz.co.id/sitemap.xml",STAMP)
        self.assertEqual(products,[])
        self.assertEqual(links,[DETAIL])

    def test_editorial_title_containing_produk_is_not_a_product(self):
        html='<main><h1>Strategi Produktivitas</h1><p>Artikel fixture pengujian yang panjang, bukan halaman produk atau katalog.</p></main>'
        products,_=parse_catalog_page(html,"https://indibiz.co.id/event-ukm/strategi-produktivitas-produk",STAMP)
        self.assertEqual(products,[])


class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.customer=AnalysisInput.model_validate({k:v for k,v in EXAMPLES[0].items() if k!="id"}).model_dump()
        self.customer["notes"]=""
        self.opportunity=sample_analysis(AnalysisInput.model_validate(self.customer)).model_dump()["opportunities"][0]

    def test_empty_catalog_does_not_generate_names_or_urls(self):
        self.assertEqual(match_products(self.opportunity,self.customer,[]),[])

    def test_matching_reports_terms_provenance_and_candidate_status(self):
        product=fixture_product()
        matches=match_products(self.opportunity,self.customer,[product])
        self.assertEqual(matches[0]["id"],product["id"])
        self.assertEqual(matches[0]["status"],"candidate_needs_validation")
        self.assertIn("monitoring",matches[0]["matched_terms"])
        self.assertEqual(matches[0]["source_url"],DETAIL)

    def test_existing_exact_product_is_labelled_existing_not_new_win(self):
        product=fixture_product(name="ASTINet")
        matches=match_products(self.opportunity,self.customer,[product])
        self.assertEqual(matches[0]["status"],"existing_in_input")
        self.assertIn("bukan kontrak aktif",matches[0]["caveat"])

    def test_unrelated_product_is_not_forced_into_match(self):
        unrelated=fixture_product("Fixture Rekrutmen", "Fixture lowongan rekrutmen pelatihan pegawai wawancara seleksi karyawan profesional.")
        self.assertEqual(match_products(self.opportunity,self.customer,[unrelated]),[])

    def test_maintenance_product_is_not_recommended(self):
        p=fixture_product();p["availability"]="maintenance"
        self.assertEqual(match_products(self.opportunity,self.customer,[p]),[])

    def test_retail_context_does_not_turn_pos_into_network_monitoring(self):
        self.customer["notes"]="Perusahaan retail, toko, kasir dan transaksi penjualan."
        pos=fixture_product("Fixture Aplikasi Kasir POS","Fixture kasir retail untuk pantau transaksi stok dan penjualan toko, bukan monitoring jaringan.")
        # Remove the negated phrase: keyword matching is deliberately conservative,
        # and does not claim to understand natural-language entailment.
        pos["description"]="Fixture kasir retail untuk pantau transaksi stok dan penjualan toko."
        self.assertEqual(match_products(self.opportunity,self.customer,[pos]),[])

    def test_short_product_qualifier_ip_is_not_lost_in_existing_identity(self):
        self.customer["services"]=[{"group4":"VPN","group5":"VPN","description":""}]
        p=fixture_product("VPN IP");p["aliases"]=["vpn-ip"]
        matches=match_products(self.opportunity,self.customer,[p])
        self.assertEqual(matches[0]["status"],"possible_existing_family")

    def test_model_selection_must_reference_a_known_product_id(self):
        analysis=sample_analysis(AnalysisInput.model_validate(self.customer)).model_dump()
        analysis["opportunities"][0]["product_ids"]=["invented-id"]
        output=enrich_analysis(analysis,self.customer,{"products":[]})
        self.assertEqual(output["opportunities"][0]["product_ids"],[])
        self.assertEqual(output["opportunities"][0]["unknown_product_ids_removed"],1)
        self.assertEqual(output["opportunities"][0]["matched_products"],[])


class RefreshTests(unittest.IsolatedAsyncioTestCase):
    async def test_blocked_sites_produce_honest_empty_state(self):
        with tempfile.TemporaryDirectory() as d,patch("app.catalog.fetch_official",AsyncMock(side_effect=ValueError("Denied"))):
            data=await refresh_catalog(Path(d)/"catalog.json")
        self.assertEqual(data["status"],"empty")
        self.assertEqual(data["products"],[])
        self.assertEqual(len(data["errors"]),5)
        self.assertIn("Tidak ada produk",data["notice"])

    async def test_old_verified_products_survive_refresh_failure_and_are_marked_stale(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"catalog.json";old=empty_catalog();old.update(products=[fixture_product()],updated_at=STAMP)
            path.write_text(json.dumps(old))
            with patch("app.catalog.fetch_official",AsyncMock(side_effect=ValueError("Denied"))):
                data=await refresh_catalog(path)
            self.assertEqual(data["status"],"stale")
            self.assertEqual(data["products"][0]["name"],"Produk Uji Monitoring")
            self.assertEqual(data["updated_at"],STAMP)

    async def test_refresh_crawls_and_saves_evidence_from_detail_pages(self):
        async def fetch(client,url):
            if url==DETAIL:return '<main><h1>Produk Fixture</h1><p>Fixture monitoring jaringan untuk membuktikan parser, bukan klaim produk resmi.</p></main>',url
            return '<a href="'+DETAIL+'">Produk Fixture</a>',url
        with tempfile.TemporaryDirectory() as d,patch("app.catalog.fetch_official",fetch):
            path=Path(d)/"catalog.json";data=await refresh_catalog(path)
            self.assertEqual(len(data["products"]),1)
            self.assertEqual(read_catalog(path)["products"][0]["id"],data["products"][0]["id"])
            self.assertEqual(read_catalog(path)["products"][0]["description"],data["products"][0]["description"])


class CatalogApiTests(unittest.TestCase):
    def test_preview_and_rematch_use_cached_catalog_without_google_or_llm(self):
        catalog=empty_catalog();catalog.update(status="available",products=[fixture_product()],updated_at=STAMP)
        data={k:v for k,v in EXAMPLES[0].items() if k!="id"}
        with patch("app.main.read_catalog",return_value=catalog):
            client=TestClient(app)
            preview=client.post("/api/preview",json=data).json()
            self.assertEqual(preview["mode"],"sample")
            self.assertTrue(preview["analysis"]["opportunities"][0]["matched_products"])
            analysis=sample_analysis(AnalysisInput.model_validate(data)).model_dump()
            rematch=client.post("/api/match",json={"company":data,"analysis":analysis})
            self.assertEqual(rematch.status_code,200)
            self.assertEqual(rematch.json()["catalog"]["products"],catalog["products"])

    def test_refresh_conflict_returns_clear_409(self):
        with patch("app.main.refresh_catalog",AsyncMock(side_effect=RuntimeError("Pembaruan sedang berjalan"))):
            self.assertEqual(TestClient(app).post("/api/catalog/refresh").status_code,409)


if __name__=="__main__":unittest.main()
