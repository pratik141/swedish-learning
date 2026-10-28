import tempfile
import unittest
from pathlib import Path

from scripts.update_context import (
    SECTIONS,
    _fingerprint,
    _stale_sections,
    _symbols,
    sections_for_path,
    sha256_file,
)


class ContextUpdaterTests(unittest.TestCase):
    def test_route_changes_map_to_behavior_and_data_flow(self):
        self.assertEqual(
            sections_for_path("sprakverkstan/routes/api.py"),
            {"CODEBASE_MAP", "BUSINESS_LOGIC", "DATA_FLOW"},
        )

    def test_unrelated_test_file_does_not_stale_behavior_notes(self):
        self.assertEqual(sections_for_path("tests/test_auth_api.py"), {"CODEBASE_MAP"})

    def test_deployment_ignore_files_stale_project_context(self):
        self.assertEqual(sections_for_path(".dockerignore"), {"PROJECT_CONTEXT"})
        self.assertEqual(sections_for_path(".gcloudignore"), {"PROJECT_CONTEXT"})

    def test_hash_and_symbol_extraction_are_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "module.py"
            source.write_text("class Example:\n    pass\n\ndef run():\n    pass\n", encoding="utf-8")
            self.assertEqual(
                _symbols("module.py", Path(directory)),
                ["Example", "run"],
            )
            first_hash = sha256_file(source)
            self.assertEqual(sha256_file(source), first_hash)
            source.write_text("class Example:\n    pass\n", encoding="utf-8")
            self.assertNotEqual(sha256_file(source), first_hash)

    def test_new_and_removed_paths_are_reported_as_stale(self):
        old_file = "sprakverkstan/routes/old_api.py"
        new_file = "sprakverkstan/routes/new_api.py"
        old_hash = "same-content"
        current = {section: {} for section in SECTIONS}
        current["BUSINESS_LOGIC"] = {new_file: old_hash}
        manifest = {
            "source_hashes": {old_file: old_hash},
            "section_hashes": {
                **{section: _fingerprint({}) for section in SECTIONS},
                "BUSINESS_LOGIC": _fingerprint({old_file: old_hash}),
            },
        }
        stale = _stale_sections(manifest, current, False)
        self.assertEqual(stale["BUSINESS_LOGIC"], [new_file, old_file])


if __name__ == "__main__":
    unittest.main()
