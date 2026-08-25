import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from compiler import FileCompileResult
from leancapsule.diagnostics_key import diagnostic_key
from leancapsule.extract import extract_theorem
from leancapsule.minimize import minimize_imports
from leancapsule.pack import pack_capsule
from leancapsule.replay import replay_capsule
from leancapsule.schema import validate_manifest


class CapsuleTest(unittest.TestCase):
    def test_diagnostic_key_is_readable_and_path_independent(self):
        left = diagnostic_key({"category": "type_mismatch", "summary": "C:\\tmp\\a.lean:2:4: bad type"})
        right = diagnostic_key({"category": "type_mismatch", "summary": "/var/tmp/b.lean:20:8: bad type"})
        self.assertEqual(left, right)
        self.assertNotIn("sha", left.lower())

    def test_manifest_schema_validation(self):
        manifest = {
            "schema_version": "leancapsule.v0.1",
            "capsule_id": "demo",
            "target": {"source_file": "Demo.lean", "selection_mode": "lines"},
            "environment": {},
            "expected": {"category": "compile_error", "diagnostic_key": "compile_error | x"},
            "provenance": {},
        }
        self.assertEqual(validate_manifest(manifest), [])

    def test_standalone_extraction_keeps_import_and_namespace(self):
        source = "import Std\nnamespace Demo\ndef helper : Nat := 1\ntheorem target : True := by trivial\nend Demo\n"
        extracted = extract_theorem(source, "Demo.target")
        self.assertIn("import Std", extracted)
        self.assertIn("namespace Demo", extracted)
        self.assertIn("theorem target", extracted)
        self.assertNotIn("def helper", extracted)

    def test_import_minimization_accepts_only_matching_key(self):
        source = "import Std\nimport Init\n\ntheorem target : True := by trivial\n"
        calls = []

        def trial(candidate):
            calls.append(candidate)
            return True, "ok | same"

        minimized, info = minimize_imports(source, trial, "ok | same")
        self.assertEqual(info["removed_imports"], 2)
        self.assertNotIn("import Std", minimized)
        self.assertEqual(len(calls), 2)

    def test_pack_writes_replayable_files_without_secret(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / "Demo.lean"
            source.write_text("import Std\nexample : True := by exact True.intro\n", encoding="utf-8")
            fake = FileCompileResult(True, 1.0, "", False, 0, ["lean", str(source)])
            with patch("leancapsule.pack.run_lean_file", return_value=fake):
                manifest = pack_capsule(base, source, base / "capsule", lines="1:2")
            self.assertEqual(manifest["expected"]["category"], "ok")
            self.assertTrue((base / "capsule" / "capsule.json").exists())
            text = (base / "capsule" / "capsule.json").read_text(encoding="utf-8")
            self.assertNotIn("secret", text.lower())

    def test_replay_matches_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            capsule = base / "capsule"
            capsule.mkdir()
            manifest = {
                "schema_version": "leancapsule.v0.1",
                "capsule_id": "demo",
                "target": {"source_file": "Demo.lean", "selection_mode": "lines"},
                "environment": {},
                "expected": {"compile_ok": False, "returncode": 1, "category": "unknown_identifier", "diagnostic_key": "unknown_identifier | unknown_identifier: Unknown identifier `missing`"},
                "provenance": {},
                "replay": {"file": "Capsule.lean"},
            }
            (capsule / "capsule.json").write_text(json.dumps(manifest), encoding="utf-8")
            (capsule / "Capsule.lean").write_text("", encoding="utf-8")
            fake = FileCompileResult(False, 1.0, "x:1:1: error: Unknown identifier `missing`", False, 1, ["lean", "Capsule.lean"])
            with patch("leancapsule.replay.run_lean_file", return_value=fake):
                result = replay_capsule(capsule)
            self.assertTrue(result["ok"])
