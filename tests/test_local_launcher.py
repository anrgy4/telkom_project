import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import run_local

spec=importlib.util.spec_from_file_location("setup_local_ai",Path(__file__).resolve().parents[1]/"scripts/setup-local-ai.py")
ai=importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai)


class LocalLauncherTests(unittest.TestCase):
    def test_existing_app_is_identified_without_installing_anything(self):
        opener=Mock()
        opener.open.return_value=io.BytesIO(json.dumps({"status":"ok","llm":{}}).encode())
        with patch("run_local.build_opener",return_value=opener):
            self.assertTrue(run_local.app_ready())

    def test_other_service_on_port_is_not_treated_as_rantai(self):
        for data in [{"status":"ok"},[],None]:
            opener=Mock();opener.open.return_value=io.BytesIO(json.dumps(data).encode())
            with patch("run_local.build_opener",return_value=opener):
                self.assertFalse(run_local.app_ready())

    def test_unchanged_installed_dependencies_and_browser_are_reused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/".runtime").mkdir();(root/"requirements.lock").write_text("example==1.0\n")
            python=root/".venv"/("Scripts/python.exe" if os.name=="nt" else "bin/python")
            python.parent.mkdir(parents=True);python.touch()
            browser=root/"browser.exe";browser.touch()
            (root/".runtime/local-dependencies.sha256").write_text(hashlib.sha256((root/"requirements.lock").read_bytes()).hexdigest())
            with patch.dict(os.environ,{"CHROMIUM_PATH":str(browser)}),patch("run_local.subprocess.run") as command:
                self.assertEqual(run_local.prepare(root),python)
                command.assert_not_called()

    def test_completed_model_does_not_download_again(self):
        with patch.object(ai,"tags",return_value=[{"name":ai.MODEL}]),patch.object(ai.opener,"open") as network,contextlib.redirect_stdout(io.StringIO()):
            ai.main()
            network.assert_not_called()

    def test_model_download_checks_finished_model_registration(self):
        data=b'{"status":"pulling","completed":50,"total":100}\n{"status":"success"}\n'
        with patch.object(ai,"tags",side_effect=[[],[{"name":ai.MODEL}]]),patch.object(ai.opener,"open",return_value=io.BytesIO(data)),contextlib.redirect_stdout(io.StringIO()) as output:
            ai.main()
            self.assertIn("Model AI siap",output.getvalue())

    def test_signed_storage_error_is_not_exposed(self):
        data=b'{"error":"https://storage.example/model?secret=not-a-real-secret denied"}\n'
        with patch.object(ai,"tags",return_value=[]),patch.object(ai.opener,"open",return_value=io.BytesIO(data)),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError) as failure:ai.main()
            self.assertNotIn("secret",str(failure.exception))


if __name__=="__main__":unittest.main()
