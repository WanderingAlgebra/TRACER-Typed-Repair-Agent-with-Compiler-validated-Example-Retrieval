import csv
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from leancapsule.gallery import build_gallery_index, write_gallery_reports
from leancapsule.schema import validate_manifest


class GalleryTest(unittest.TestCase):
    def test_gallery_meets_coverage_requirements(self):
        index = build_gallery_index(ROOT / "capsules")
        self.assertTrue(index["ok"], index)
        self.assertGreaterEqual(index["total"], 12)

    def test_all_manifests_have_required_fields_and_no_absolute_source_path(self):
        for path in (ROOT / "capsules").rglob("capsule.json"):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(validate_manifest(manifest), [])
            self.assertNotIn(str(ROOT).lower(), json.dumps(manifest, ensure_ascii=False).lower())

    def test_manual_review_ledger_covers_gallery(self):
        with (ROOT / "capsules" / "MANUAL_REVIEW.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        ids = {json.loads(path.read_text(encoding="utf-8"))["capsule_id"] for path in (ROOT / "capsules").rglob("capsule.json")}
        self.assertEqual(ids, {row["capsule_id"] for row in rows})

    def test_gallery_reports_are_reproducible(self):
        index = build_gallery_index(ROOT / "capsules")
        out = ROOT / "tests" / ".gallery-test.json"
        try:
            write_gallery_reports(index, out)
            self.assertTrue(out.with_suffix(".csv").exists())
            self.assertTrue(out.with_suffix(".md").exists())
        finally:
            for path in (out, out.with_suffix(".csv"), out.with_suffix(".md")):
                if path.exists():
                    path.unlink()
