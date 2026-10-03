import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "incident.json"


class CliTests(unittest.TestCase):
    def run_text(self, payload, *args):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "input.json"
            file.write_text(payload, encoding="utf-8")
            return subprocess.run([sys.executable, "-m", "incidentinterval.cli", str(file), *args],
                                  text=True, capture_output=True, check=False)

    def test_installable_entrypoint_workflow(self):
        out = self.run_text(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)["status"], "ANALYZED")

    def test_duplicate_json_and_nonfinite(self):
        for text in ['{"version": 1, "version": 1}', '{"x": NaN}', "{"]:
            out = self.run_text(text)
            self.assertEqual(out.returncode, 2)
            self.assertEqual(json.loads(out.stderr)["status"], "INVALID_INPUT")

    def test_missing_file_is_machine_readable(self):
        out = subprocess.run([sys.executable, "-m", "incidentinterval.cli", "definitely_missing.json"],
                             text=True, capture_output=True)
        self.assertEqual(out.returncode, 2)
        self.assertEqual(json.loads(out.stderr)["status"], "INVALID_INPUT")

    def test_baseline_and_invalid_limit(self):
        out = self.run_text(FIXTURE.read_text(encoding="utf-8"), "--baseline")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)["selected_intervention"], "rate_limit")
        self.assertEqual(self.run_text("{}", "--max-branches", "0").returncode, 2)
