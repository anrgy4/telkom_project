import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.domain import AnalysisInput, EXAMPLES, PRIMARY, SUPPORT, parse_table, sample_analysis
from app.llm import ollama_url, validate_grounding
from app.main import app
from app.research import ResearchError, parse_google, public_url, search_google
import httpx


def input_data(index=0):
    return AnalysisInput.model_validate({k:v for k,v in EXAMPLES[index].items() if k != "id"})


class CustomerDataTests(unittest.TestCase):
    def test_five_sectors_match_the_screenshots(self):
        self.assertEqual([x["sector"] for x in EXAMPLES], ["retail", "education", "health", "bank", "cooperative"])
        self.assertEqual([s["group5"] for s in EXAMPLES[3]["services"]], ["ASTINet", "OCA", "VPN"])
        self.assertEqual(EXAMPLES[0]["company"], "KOPONTRES SIDOGIRI")

    def test_pivot_fill_down_resets_at_company_and_parent_change(self):
        table = "STANDARD_NAME\tWITEL_HO\tGROUP4\tGROUP5\tDESC2\nA CORP\tW1\tASTINet\tASTINet\tDedicated\n\t\t\t\tRevenue Recognition\n\t\tCloud\t\tCloud IDC\nB CORP\tW2\tVPN\tVPN\tIntranet\n"
        companies = parse_table(table)["companies"]
        self.assertEqual(len(companies), 2)
        self.assertEqual(companies[0]["services"][1]["description"], "Revenue Recognition")
        self.assertEqual(companies[0]["services"][2]["group5"], "Cloud")
        self.assertEqual(companies[1]["services"][0]["group4"], "VPN")

    def test_csv_quoted_comma_and_semicolon(self):
        for delim in [",", ";"]:
            table = delim.join(["STANDARD_NAME","WITEL_HO","GROUP4","GROUP5","DESC2"]) + "\n" + delim.join(['"A, B"',"W1","VPN","VPN",'"Dedicated, service"'])
            out = parse_table(table)["companies"][0]
            self.assertEqual(out["company"], "A, B")
            self.assertEqual(out["services"][0]["description"], "Dedicated, service")

    def test_invalid_header_is_actionable(self):
        with self.assertRaisesRegex(ValueError, "Header wajib"):
            parse_table("name,service\nA,VPN")

    def test_pivot_description_is_not_carried_forward(self):
        table = "STANDARD_NAME,WITEL_HO,GROUP4,GROUP5,DESC2\nA,W,VPN,VPN,First\n,,,,\n"
        self.assertEqual(parse_table(table)["companies"][0]["services"][1]["description"], "")


class GroundingTests(unittest.TestCase):
    def test_complete_sample_for_every_sector_is_hypothesis(self):
        for index in range(5):
            result = sample_analysis(input_data(index))
            self.assertEqual([a.name for a in result.support], SUPPORT)
            self.assertEqual([a.name for a in result.primary], PRIMARY)
            self.assertTrue(all(i.basis == "hypothesis" for a in result.primary+result.support for i in a.items))

    def test_unknown_citation_and_nonmatching_quote_are_downgraded(self):
        data = input_data(); result = sample_analysis(data)
        result.overview.basis = "public"; result.overview.source_ids = ["S999"]
        result.overview.evidence_quote = "invented evidence"
        result, count = validate_grounding(result, data, [{"id":"S1","text":"actual evidence"}])
        self.assertEqual(count, 1)
        self.assertEqual(result.overview.basis, "hypothesis")
        self.assertEqual(result.overview.source_ids, [])

    def test_matching_quote_and_source_are_retained(self):
        data = input_data(); result = sample_analysis(data)
        result.overview.basis = "public"; result.overview.source_ids = ["S1"]
        result.overview.evidence_quote = "retail stores"
        result, count = validate_grounding(result, data, [{"id":"S1","text":"Company operates retail stores in Java."}])
        self.assertEqual(count, 0)
        self.assertEqual(result.overview.basis, "public")

    def test_ungrounded_customer_claim_is_downgraded(self):
        data=input_data(); result=sample_analysis(data)
        result.overview.basis="customer";result.overview.evidence_quote="revenue doubled"
        result,count=validate_grounding(result,data,[])
        self.assertEqual(count,1)
        self.assertEqual(result.overview.basis,"hypothesis")

    def test_wrong_activity_order_is_rejected(self):
        data=input_data(); result=sample_analysis(data); result.primary.reverse()
        with self.assertRaisesRegex(ValueError,"susunan"):
            validate_grounding(result,data,[])

    def test_remote_llm_and_url_credentials_are_rejected(self):
        for url in ["https://cloud.example.com", "http://localhost.evil.test", "http://user:pass@127.0.0.1:11434", "http://127.0.0.1:11434/api"]:
            with patch.dict(os.environ,{"OLLAMA_BASE_URL":url}):
                with self.assertRaises(ValueError): ollama_url()


class SearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_private_destinations_are_rejected(self):
        for url in ["http://localhost/", "http://127.0.0.1", "http://169.254.169.254/latest", "file:///etc/passwd", "http://10.0.0.1", "http://[::1]", "https://example.com:11434"]:
            self.assertFalse(await public_url(url),url)

    async def test_google_results_extract_links_and_ignore_google_navigation(self):
        html='<div><a href="/url?q=https%3A%2F%2Fexample.org%2Fcompany"><h3>Company Profile</h3></a><p>Trusted snippet</p></div><a href="https://www.google.com/search?q=more"><h3>More</h3></a>'
        sources=parse_google(html)
        self.assertEqual(len(sources),1)
        self.assertEqual(sources[0]["url"],"https://example.org/company")
        self.assertIn("Trusted snippet",sources[0]["snippet"])

    async def test_captcha_is_a_failure_not_empty_success(self):
        with self.assertRaises(ResearchError):
            parse_google('<form action="/sorry/index"><h3>Verify</h3></form>')

    async def test_indonesian_captcha_and_javascript_pages_are_failures(self):
        with self.assertRaisesRegex(ResearchError,"CAPTCHA"):
            parse_google('<p>Sistem kami telah mendeteksi adanya lalu lintas yang tidak wajar dari jaringan komputer Anda.</p>')
        with self.assertRaisesRegex(ResearchError,"JavaScript"):
            parse_google('<a href="/httpservice/retry/enablejs?test=1">here</a>')

    async def test_javascript_page_uses_normal_browser_renderer(self):
        renderer=AsyncMock(return_value=[{"url":"https://example.org","title":"Company","snippet":"Evidence"}])
        html='<a href="/httpservice/retry/enablejs">here</a>'
        with patch("app.research.bounded_html",AsyncMock(return_value=html)),patch("app.research.rendered_google",renderer):
            sources=await search_google(None,"Company name only")
        self.assertEqual(sources[0]["url"],"https://example.org")
        renderer.assert_awaited_once()

    async def test_captcha_does_not_trigger_browser_retry(self):
        renderer=AsyncMock()
        with patch("app.research.bounded_html",AsyncMock(return_value='<form action="/sorry/index"></form>')),patch("app.research.rendered_google",renderer):
            with self.assertRaisesRegex(ResearchError,"CAPTCHA"):
                await search_google(None,"Company")
        renderer.assert_not_awaited()


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(app)
        from app.catalog import empty_catalog
        catalog=empty_catalog();catalog['last_attempt_at']='test-no-network'
        patcher=patch('app.main.read_catalog',return_value=catalog)
        patcher.start();self.addCleanup(patcher.stop)

    def test_home_and_sample_api_work_without_model(self):
        self.assertEqual(self.client.get("/").status_code,200)
        self.assertIn("Kenali bisnisnya", self.client.get("/").text)
        for i in range(5):
            r=self.client.post("/api/preview",json=input_data(i).model_dump())
            self.assertEqual(r.status_code,200)
            self.assertEqual(r.json()["mode"],"sample")
            self.assertIsNone(r.json()["model"])
            self.assertEqual(r.json()["sources"],[])

    def test_missing_model_returns_503_without_fake_output(self):
        with patch("app.main.model_status",AsyncMock(return_value={"ready":False,"message":"Ollama lokal belum aktif"})):
            response=self.client.post("/api/analyze",json=input_data().model_dump())
        self.assertEqual(response.status_code,503)
        self.assertNotIn("analysis",response.json())

    def test_stream_contract_with_mocked_dependencies(self):
        data=input_data(); sources=[{"id":"S1","text":"Evidence","url":"https://example.org"}]
        async def fake_research(company,sector,notify):
            await notify("search","Mencari…")
            return {"query":company,"sources":sources}
        with patch("app.main.model_status",AsyncMock(return_value={"ready":True})), patch("app.main.research",fake_research), patch("app.main.generate",AsyncMock(return_value=(sample_analysis(data),0))):
            r=self.client.post("/api/analyze",json=data.model_dump())
        events=[json.loads(line) for line in r.text.splitlines()]
        self.assertEqual([e["type"] for e in events],["progress","research","result"])
        self.assertEqual(events[-1]["data"]["mode"],"live")
        self.assertEqual(events[-1]["data"]["sources"],sources)

    def test_research_failure_does_not_invoke_llm_or_return_sample(self):
        generator=AsyncMock()
        with patch("app.main.model_status",AsyncMock(return_value={"ready":True})), patch("app.main.research",AsyncMock(side_effect=ResearchError("Google denied"))), patch("app.main.generate",generator):
            r=self.client.post("/api/analyze",json=input_data().model_dump())
        events=[json.loads(line) for line in r.text.splitlines()]
        self.assertEqual(events,[{"type":"error","message":"Google denied"}])
        generator.assert_not_awaited()

    def test_import_returns_separate_companies(self):
        r=self.client.post("/api/import",json={"text":"STANDARD_NAME,WITEL_HO,GROUP4,GROUP5,DESC2\nA,W,VPN,VPN,Desc\nB,X,Cloud,Cloud,Desc"})
        self.assertEqual(len(r.json()["companies"]),2)

    def test_unknown_sector_and_missing_company_fail_validation(self):
        data=input_data().model_dump();data["sector"]="guessed";data["company"]=""
        self.assertEqual(self.client.post("/api/analyze",json=data).status_code,422)


if __name__=="__main__":unittest.main()
