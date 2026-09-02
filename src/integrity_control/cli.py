from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .database import load_hash_database, save_hash_database
from .demo import run_aerospace_demo
from .reports import export_pdf_report, export_txt_report
from .scanner import compare_records, scan_folder


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _print_report_summary(report) -> None:
    summary = report.summary()
    print(f"Статус: {report.status}")
    print(f"Файлов сейчас: {summary['total_current_files']}")
    print(f"Без изменений: {summary['unchanged']}")
    print(f"Новых: {summary['new']}")
    print(f"Измененных: {summary['changed']}")
    print(f"Удаленных: {summary['deleted']}")

    if report.new_files:
        print("\nНовые файлы:")
        for record in report.new_files:
            print(f"  + {record.path}")

    if report.changed_files:
        print("\nИзмененные файлы:")
        for record in report.changed_files:
            print(f"  * {record.path}")

    if report.deleted_files:
        print("\nУдаленные файлы:")
        for record in report.deleted_files:
            print(f"  - {record.path}")


def create_database(folder: Path, database_path: Path) -> int:
    ignored_paths = {database_path}
    records = scan_folder(folder, ignored_paths=ignored_paths)
    save_hash_database(records, database_path, folder)
    print(f"База хэшей создана: {database_path}")
    print(f"Контролируемых файлов: {len(records)}")
    return 0


def check_integrity(
    folder: Path,
    database_path: Path,
    txt_report: Path | None = None,
    pdf_report: Path | None = None,
    fail_on_change: bool = False,
) -> int:
    baseline, _metadata = load_hash_database(database_path)
    ignored_paths = {database_path}

    if txt_report:
        ignored_paths.add(txt_report)
    if pdf_report:
        ignored_paths.add(pdf_report)

    current = scan_folder(folder, ignored_paths=ignored_paths)
    report = compare_records(baseline, current, folder, database_path)
    _print_report_summary(report)

    if txt_report:
        export_txt_report(report, txt_report)
        print(f"\nTXT-отчет сохранен: {txt_report}")

    if pdf_report:
        export_pdf_report(report, pdf_report)
        print(f"PDF-отчет сохранен: {pdf_report}")

    return 2 if fail_on_change and report.has_violations else 0


def scan_command(folder: Path) -> int:
    records = scan_folder(folder)
    print(f"Найдено файлов: {len(records)}")

    for path in sorted(records):
        record = records[path]
        print(f"{record.sha256}  {record.path}")

    return 0


def demo_command() -> int:
    paths = run_aerospace_demo(_project_root())
    print("Демонстрация выполнена.")
    print(f"Рабочая копия: {paths['controlled_folder']}")
    print(f"База хэшей: {paths['database']}")
    print(f"TXT-отчет: {paths['txt_report']}")
    print(f"PDF-отчет: {paths['pdf_report']}")
    return 0


def menu_command() -> int:
    while True:
        print("\nКонтроль целостности файлов")
        print("1. Создать базу хэшей")
        print("2. Проверить папку по базе")
        print("3. Показать SHA-256 файлов папки")
        print("4. Запустить демонстрацию")
        print("0. Выход")

        choice = input("Выберите действие: ").strip()

        try:
            if choice == "1":
                folder = _resolve_path(input("Папка для контроля: ").strip())
                default_db = _project_root() / "hashes" / "hashes.json"
                raw_db = input(f"Файл базы [{default_db}]: ").strip()
                database_path = _resolve_path(raw_db) if raw_db else default_db
                create_database(folder, database_path)
            elif choice == "2":
                folder = _resolve_path(input("Папка для проверки: ").strip())
                database_path = _resolve_path(input("Файл базы хэшей: ").strip())
                raw_txt = input("TXT-отчет (Enter - не сохранять): ").strip()
                raw_pdf = input("PDF-отчет (Enter - не сохранять): ").strip()
                check_integrity(
                    folder,
                    database_path,
                    _resolve_path(raw_txt) if raw_txt else None,
                    _resolve_path(raw_pdf) if raw_pdf else None,
                )
            elif choice == "3":
                folder = _resolve_path(input("Папка для просмотра: ").strip())
                scan_command(folder)
            elif choice == "4":
                demo_command()
            elif choice == "0":
                return 0
            else:
                print("Неизвестное действие.")
        except Exception as exc:
            print(f"Ошибка: {exc}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="integrity-control",
        description="Контроль целостности файлов с использованием SHA-256.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="создать базу хэшей для папки")
    init_parser.add_argument("folder", help="папка для контроля")
    init_parser.add_argument("database", help="путь для JSON-базы хэшей")

    check_parser = subparsers.add_parser("check", help="проверить папку по базе хэшей")
    check_parser.add_argument("folder", help="папка для проверки")
    check_parser.add_argument("database", help="существующая JSON-база хэшей")
    check_parser.add_argument("--txt", help="сохранить TXT-отчет")
    check_parser.add_argument("--pdf", help="сохранить PDF-отчет")
    check_parser.add_argument(
        "--fail-on-change",
        action="store_true",
        help="вернуть код 2, если найдены нарушения целостности",
    )

    scan_parser = subparsers.add_parser("scan", help="показать SHA-256 файлов папки")
    scan_parser.add_argument("folder", help="папка для сканирования")

    subparsers.add_parser("demo", help="запустить демонстрацию на аэрокосмических данных")
    subparsers.add_parser("menu", help="запустить интерактивное меню")
    subparsers.add_parser("gui", help="запустить графический интерфейс")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            return create_database(_resolve_path(args.folder), _resolve_path(args.database))
        if args.command == "check":
            return check_integrity(
                _resolve_path(args.folder),
                _resolve_path(args.database),
                _resolve_path(args.txt) if args.txt else None,
                _resolve_path(args.pdf) if args.pdf else None,
                args.fail_on_change,
            )
        if args.command == "scan":
            return scan_command(_resolve_path(args.folder))
        if args.command == "demo":
            return demo_command()
        if args.command == "menu":
            return menu_command()
        if args.command == "gui":
            from .gui import run_gui

            return run_gui()
    except Exception as exc:
        print(f"Ошибка: {exc}")
        return 1

    parser.print_help()
    return 1
