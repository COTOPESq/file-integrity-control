from __future__ import annotations

import html
import os
import textwrap
from pathlib import Path

from .models import FileRecord, IntegrityReport


def _short_hash(value: str) -> str:
    return f"{value[:12]}..."


def _format_file_record(record: FileRecord) -> str:
    return f"{record.path} | размер: {record.size} байт | SHA-256: {_short_hash(record.sha256)}"


def build_text_report(report: IntegrityReport) -> str:
    """Build a plain text report that is easy to include in coursework."""
    summary = report.summary()
    lines = [
        "ОТЧЕТ О КОНТРОЛЕ ЦЕЛОСТНОСТИ ФАЙЛОВ",
        "=" * 44,
        f"Дата проверки: {report.generated_at}",
        f"Контролируемая папка: {report.controlled_folder}",
        f"База хэшей: {report.database_path}",
        f"Статус: {report.status}",
        "",
        "Сводка:",
        f"- файлов сейчас: {summary['total_current_files']}",
        f"- без изменений: {summary['unchanged']}",
        f"- новых: {summary['new']}",
        f"- измененных: {summary['changed']}",
        f"- удаленных: {summary['deleted']}",
        "",
    ]

    if report.new_files:
        lines.append("Новые файлы:")
        lines.extend(f"+ {_format_file_record(record)}" for record in report.new_files)
        lines.append("")

    if report.changed_files:
        lines.append("Измененные файлы:")
        for record in report.changed_files:
            lines.append(f"* {record.path}")
            lines.append(f"  старый SHA-256: {_short_hash(record.old_sha256)}")
            lines.append(f"  новый SHA-256:  {_short_hash(record.new_sha256)}")
            lines.append(f"  размер: {record.old_size} -> {record.new_size} байт")
        lines.append("")

    if report.deleted_files:
        lines.append("Удаленные файлы:")
        lines.extend(f"- {_format_file_record(record)}" for record in report.deleted_files)
        lines.append("")

    if not report.has_violations:
        lines.append("Нарушений целостности не обнаружено.")

    lines.append("Примечание: SHA-256 показывает факт изменения содержимого, но не сообщает причину изменения.")
    return "\n".join(lines) + "\n"


def export_txt_report(report: IntegrityReport, output_path: Path) -> None:
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_text_report(report), encoding="utf-8")


def _font_candidates() -> list[tuple[str, str]]:
    configured = os.getenv("INTEGRITY_PDF_FONT")
    candidates = []
    if configured:
        candidates.append(("IntegrityFont", configured))

    candidates.extend(
        [
            ("IntegrityFont", "C:/Windows/Fonts/arial.ttf"),
            ("IntegrityFont", "C:/Windows/Fonts/calibri.ttf"),
            ("IntegrityFont", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            ("IntegrityFont", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
            ("IntegrityFont", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        ]
    )
    return candidates


def _register_pdf_font() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for font_name, font_path in _font_candidates():
        path = Path(font_path)
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont(font_name, str(path)))
                return font_name
            except Exception:
                continue

    return "Helvetica"


def _paragraph(text: str, style):
    from reportlab.platypus import Paragraph

    return Paragraph(html.escape(text), style)


def _table_cell(text: str, style):
    from reportlab.platypus import Paragraph

    escaped = html.escape(text)
    wrapped = escaped.replace("/", "/<wbr/>").replace("\\", "\\<wbr/>")
    return Paragraph(wrapped, style)


def _add_section(title: str, rows: list[list[str]], story: list, styles: dict[str, object]) -> None:
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    story.append(Spacer(1, 10))
    story.append(Paragraph(html.escape(title), styles["heading"]))
    table_rows = [[_table_cell(cell, styles["table"]) for cell in row] for row in rows]
    table = Table(table_rows, colWidths=[190, 300], repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9EEF7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C9D2E3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)


def export_pdf_report(report: IntegrityReport, output_path: Path) -> None:
    """Export report as PDF. Requires the reportlab package."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise RuntimeError("Для экспорта PDF установите зависимость: pip install reportlab") from exc

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    font_name = _register_pdf_font()
    styles = {
        "title": ParagraphStyle(
            "Title",
            fontName=font_name,
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=10,
        ),
        "normal": ParagraphStyle(
            "Normal",
            fontName=font_name,
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#263238"),
        ),
        "heading": ParagraphStyle(
            "Heading",
            fontName=font_name,
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=5,
        ),
        "table": ParagraphStyle(
            "Table",
            fontName=font_name,
            fontSize=8.2,
            leading=10.5,
            wordWrap="CJK",
            textColor=colors.HexColor("#263238"),
        ),
    }

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Отчет о контроле целостности файлов",
    )

    summary = report.summary()
    story: list = [
        _paragraph("Отчет о контроле целостности файлов", styles["title"]),
        _paragraph(f"Дата проверки: {report.generated_at}", styles["normal"]),
        _paragraph(f"Контролируемая папка: {report.controlled_folder}", styles["normal"]),
        _paragraph(f"База хэшей: {report.database_path}", styles["normal"]),
        Spacer(1, 8),
    ]

    status_color = "#FDECEC" if report.has_violations else "#EAF7EF"
    status_table = Table(
        [[_table_cell("Статус", styles["table"]), _table_cell(report.status, styles["table"])]],
        colWidths=[120, 370],
        hAlign="LEFT",
    )
    status_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(status_color)),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#BFC8D8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(status_table)

    _add_section(
        "Сводка",
        [
            ["Показатель", "Значение"],
            ["Файлов сейчас", str(summary["total_current_files"])],
            ["Без изменений", str(summary["unchanged"])],
            ["Новых", str(summary["new"])],
            ["Измененных", str(summary["changed"])],
            ["Удаленных", str(summary["deleted"])],
        ],
        story,
        styles,
    )

    if report.new_files:
        _add_section(
            "Новые файлы",
            [["Файл", "Сведения"]]
            + [
                [record.path, f"Размер: {record.size} байт; SHA-256: {_short_hash(record.sha256)}"]
                for record in report.new_files
            ],
            story,
            styles,
        )

    if report.changed_files:
        _add_section(
            "Измененные файлы",
            [["Файл", "Изменение"]]
            + [
                [
                    record.path,
                    textwrap.dedent(
                        f"""\
                        Старый SHA-256: {_short_hash(record.old_sha256)}
                        Новый SHA-256: {_short_hash(record.new_sha256)}
                        Размер: {record.old_size} -> {record.new_size} байт"""
                    ),
                ]
                for record in report.changed_files
            ],
            story,
            styles,
        )

    if report.deleted_files:
        _add_section(
            "Удаленные файлы",
            [["Файл", "Сведения из базы"]]
            + [
                [record.path, f"Размер: {record.size} байт; SHA-256: {_short_hash(record.sha256)}"]
                for record in report.deleted_files
            ],
            story,
            styles,
        )

    if not report.has_violations:
        story.append(Spacer(1, 10))
        story.append(_paragraph("Нарушений целостности не обнаружено.", styles["normal"]))

    story.append(Spacer(1, 12))
    story.append(
        _paragraph(
            "Примечание: SHA-256 показывает факт изменения содержимого, но не сообщает причину изменения.",
            styles["normal"],
        )
    )

    document.build(story)
