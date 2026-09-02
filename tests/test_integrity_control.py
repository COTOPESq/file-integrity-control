from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from integrity_control.database import load_hash_database, save_hash_database
from integrity_control.hashing import sha256_file
from integrity_control.reports import export_pdf_report, export_txt_report
from integrity_control.scanner import compare_records, scan_folder
from integrity_control.cli import build_parser


class HashingTests(unittest.TestCase):
    def test_sha256_file_for_known_content(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            sample = tmp / "sample.txt"
            sample.write_text("abc", encoding="utf-8")

            self.assertEqual(
                sha256_file(sample),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            )


class IntegrityScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw_tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self.raw_tmp.name)
        self.controlled = self.tmp / "controlled"
        self.controlled.mkdir()
        (self.controlled / "telemetry.txt").write_text("altitude=420\n", encoding="utf-8")
        (self.controlled / "config.ini").write_text("[nav]\nmode=nominal\n", encoding="utf-8")
        self.database = self.tmp / "hashes.json"

    def tearDown(self) -> None:
        self.raw_tmp.cleanup()

    def test_database_round_trip(self) -> None:
        records = scan_folder(self.controlled)
        save_hash_database(records, self.database, self.controlled)
        loaded, metadata = load_hash_database(self.database)

        self.assertEqual(set(records), set(loaded))
        self.assertEqual(metadata["algorithm"], "SHA-256")

    def test_compare_detects_new_changed_and_deleted_files(self) -> None:
        baseline = scan_folder(self.controlled)
        save_hash_database(baseline, self.database, self.controlled)

        (self.controlled / "telemetry.txt").write_text("altitude=421\n", encoding="utf-8")
        (self.controlled / "new_plan.txt").write_text("switch payload to standby\n", encoding="utf-8")
        (self.controlled / "config.ini").unlink()

        current = scan_folder(self.controlled)
        report = compare_records(baseline, current, self.controlled, self.database)

        self.assertTrue(report.has_violations)
        self.assertEqual([item.path for item in report.new_files], ["new_plan.txt"])
        self.assertEqual([item.path for item in report.deleted_files], ["config.ini"])
        self.assertEqual([item.path for item in report.changed_files], ["telemetry.txt"])

    def test_report_exports(self) -> None:
        baseline = scan_folder(self.controlled)
        (self.controlled / "telemetry.txt").write_text("altitude=421\n", encoding="utf-8")
        current = scan_folder(self.controlled)
        report = compare_records(baseline, current, self.controlled, self.database)

        txt_report = self.tmp / "report.txt"
        pdf_report = self.tmp / "report.pdf"
        export_txt_report(report, txt_report)
        self.assertIn("Измененные файлы", txt_report.read_text(encoding="utf-8"))

        try:
            export_pdf_report(report, pdf_report)
        except RuntimeError as exc:
            self.skipTest(str(exc))

        self.assertTrue(pdf_report.exists())
        self.assertGreater(pdf_report.stat().st_size, 1000)


class DemoDataTests(unittest.TestCase):
    def test_aerospace_demo_data_is_scannable(self) -> None:
        source = PROJECT_ROOT / "data" / "aerospace_demo"
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            controlled = tmp / "aerospace_demo"
            shutil.copytree(source, controlled)

            records = scan_folder(controlled)

        self.assertGreaterEqual(len(records), 4)
        self.assertIn("telemetry/orbit_status.txt", records)


class CliTests(unittest.TestCase):
    def test_gui_command_is_registered(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["gui"])

        self.assertEqual(args.command, "gui")


if __name__ == "__main__":
    unittest.main()
