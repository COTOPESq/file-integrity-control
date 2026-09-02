from __future__ import annotations

import shutil
from pathlib import Path

from .database import save_hash_database
from .reports import export_pdf_report, export_txt_report
from .scanner import compare_records, scan_folder


def run_aerospace_demo(project_root: Path) -> dict[str, Path]:
    """Run a complete demonstration on aerospace-themed sample files."""
    source = project_root / "data" / "aerospace_demo"
    workspace = project_root / "examples" / "demo_workspace"
    controlled_folder = workspace / "aerospace_demo_current"
    results_dir = project_root / "examples" / "results"

    if workspace.exists():
        shutil.rmtree(workspace)

    controlled_folder.parent.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, controlled_folder)

    database_path = results_dir / "aerospace_hashes.json"
    txt_report = results_dir / "integrity_report.txt"
    pdf_report = results_dir / "integrity_report.pdf"

    baseline = scan_folder(controlled_folder)
    save_hash_database(baseline, database_path, controlled_folder)

    orbit_file = controlled_folder / "telemetry" / "orbit_status.txt"
    orbit_file.write_text(
        orbit_file.read_text(encoding="utf-8")
        + "\n2026-08-25T10:24:00Z; corrective burn command appended after baseline\n",
        encoding="utf-8",
    )

    new_plan = controlled_folder / "mission_docs" / "thermal_recovery_plan.txt"
    new_plan.write_text(
        "Emergency thermal recovery plan for low Earth orbit spacecraft.\n"
        "Step 1: switch payload to standby mode.\n"
        "Step 2: rotate solar arrays to nominal safe angle.\n",
        encoding="utf-8",
    )

    deleted_file = controlled_folder / "payload" / "sensor_calibration.json"
    deleted_file.unlink()

    current = scan_folder(controlled_folder)
    report = compare_records(baseline, current, controlled_folder, database_path)
    export_txt_report(report, txt_report)
    export_pdf_report(report, pdf_report)

    return {
        "controlled_folder": controlled_folder,
        "database": database_path,
        "txt_report": txt_report,
        "pdf_report": pdf_report,
    }
