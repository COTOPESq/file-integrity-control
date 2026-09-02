from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .database import load_hash_database, save_hash_database
from .demo import run_aerospace_demo
from .reports import build_text_report, export_pdf_report, export_txt_report
from .scanner import compare_records, scan_folder


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _as_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _reportlab_available() -> bool:
    return importlib.util.find_spec("reportlab") is not None


class IntegrityControlApp:
    """Minimal Tkinter interface for the integrity control tool."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Контроль целостности файлов SHA-256")
        self.root.geometry("920x640")
        self.root.minsize(780, 560)

        project_root = _project_root()
        self.folder_var = tk.StringVar(value=str(project_root / "data" / "aerospace_demo"))
        self.database_var = tk.StringVar(value=str(project_root / "hashes" / "hashes.json"))
        self.txt_report_var = tk.StringVar(value=str(project_root / "reports" / "integrity_report.txt"))
        self.pdf_report_var = tk.StringVar(value=str(project_root / "reports" / "integrity_report.pdf"))
        self.export_txt_var = tk.BooleanVar(value=True)
        self.export_pdf_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Выберите папку и создайте базу хэшей.")

        self._configure_style()
        self._build_layout()

    def _configure_style(self) -> None:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Action.TButton", padding=(10, 6))

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        frame = ttk.Frame(self.root, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(7, weight=1)

        ttk.Label(frame, text="Контроль целостности файлов", style="Title.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 12)
        )

        self._path_row(frame, 1, "Папка:", self.folder_var, self._choose_folder)
        self._path_row(frame, 2, "База хэшей:", self.database_var, self._choose_database)

        ttk.Checkbutton(frame, text="TXT-отчет", variable=self.export_txt_var).grid(
            row=3, column=0, sticky="w", pady=4
        )
        ttk.Entry(frame, textvariable=self.txt_report_var).grid(row=3, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(frame, text="Выбрать", command=self._choose_txt_report).grid(row=3, column=2, sticky="ew", pady=4)

        ttk.Checkbutton(frame, text="PDF-отчет", variable=self.export_pdf_var).grid(
            row=4, column=0, sticky="w", pady=4
        )
        ttk.Entry(frame, textvariable=self.pdf_report_var).grid(row=4, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(frame, text="Выбрать", command=self._choose_pdf_report).grid(row=4, column=2, sticky="ew", pady=4)

        actions = ttk.Frame(frame)
        actions.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(12, 10))
        actions.columnconfigure((0, 1, 2, 3), weight=1)

        ttk.Button(
            actions,
            text="Создать базу хэшей",
            style="Action.TButton",
            command=self.create_database,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(
            actions,
            text="Проверить целостность",
            style="Action.TButton",
            command=self.check_integrity,
        ).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(
            actions,
            text="Демо ORBIS-2",
            style="Action.TButton",
            command=self.run_demo,
        ).grid(row=0, column=2, sticky="ew", padx=8)
        ttk.Button(
            actions,
            text="Очистить журнал",
            style="Action.TButton",
            command=self.clear_log,
        ).grid(row=0, column=3, sticky="ew", padx=(8, 0))

        ttk.Label(frame, textvariable=self.status_var, style="Status.TLabel").grid(
            row=6, column=0, columnspan=4, sticky="w", pady=(0, 6)
        )

        self.log = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=18, font=("Consolas", 10))
        self.log.grid(row=7, column=0, columnspan=4, sticky="nsew")
        self.log.insert(tk.END, "Журнал работы программы.\n")

    def _path_row(self, frame: ttk.Frame, row: int, label: str, variable: tk.StringVar, command) -> None:
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(frame, text="Выбрать", command=command).grid(row=row, column=2, sticky="ew", pady=4)

    def _choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="Выберите папку для контроля")
        if folder:
            self.folder_var.set(folder)

    def _choose_database(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Выберите файл базы хэшей",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Все файлы", "*.*")],
        )
        if path:
            self.database_var.set(path)

    def _choose_txt_report(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Куда сохранить TXT-отчет",
            defaultextension=".txt",
            filetypes=[("TXT", "*.txt"), ("Все файлы", "*.*")],
        )
        if path:
            self.txt_report_var.set(path)
            self.export_txt_var.set(True)

    def _choose_pdf_report(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Куда сохранить PDF-отчет",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf"), ("Все файлы", "*.*")],
        )
        if path:
            self.pdf_report_var.set(path)
            self.export_pdf_var.set(True)

    def _log(self, message: str) -> None:
        self.log.insert(tk.END, f"\n{message}\n")
        self.log.see(tk.END)

    def _set_busy(self, busy: bool) -> None:
        self.root.config(cursor="watch" if busy else "")
        self.root.update_idletasks()

    def _selected_folder(self) -> Path:
        value = self.folder_var.get().strip()
        if not value:
            raise ValueError("Не выбрана папка для контроля.")
        return _as_path(value)

    def _selected_database(self) -> Path:
        value = self.database_var.get().strip()
        if not value:
            raise ValueError("Не выбран файл базы хэшей.")
        return _as_path(value)

    def create_database(self) -> None:
        try:
            self._set_busy(True)
            folder = self._selected_folder()
            database_path = self._selected_database()
            records = scan_folder(folder, ignored_paths={database_path})
            save_hash_database(records, database_path, folder)

            self.status_var.set(f"База создана. Файлов: {len(records)}")
            self._log(f"База хэшей создана:\n{database_path}\nКонтролируемых файлов: {len(records)}")
            messagebox.showinfo("Готово", f"База хэшей создана.\nФайлов: {len(records)}")
        except Exception as exc:
            self._show_error(exc)
        finally:
            self._set_busy(False)

    def check_integrity(self) -> None:
        try:
            self._set_busy(True)
            folder = self._selected_folder()
            database_path = self._selected_database()
            baseline, _metadata = load_hash_database(database_path)

            txt_report = _as_path(self.txt_report_var.get()) if self.export_txt_var.get() else None
            pdf_report = _as_path(self.pdf_report_var.get()) if self.export_pdf_var.get() else None
            ignored_paths = {database_path}
            if txt_report:
                ignored_paths.add(txt_report)
            if pdf_report:
                ignored_paths.add(pdf_report)

            current = scan_folder(folder, ignored_paths=ignored_paths)
            report = compare_records(baseline, current, folder, database_path)

            if txt_report:
                export_txt_report(report, txt_report)
            if pdf_report:
                self._ensure_pdf_dependency()
                export_pdf_report(report, pdf_report)

            summary = report.summary()
            self.status_var.set(
                f"{report.status}: новых {summary['new']}, измененных {summary['changed']}, "
                f"удаленных {summary['deleted']}"
            )
            self._log(build_text_report(report))
            messagebox.showinfo("Проверка завершена", self.status_var.get())
        except Exception as exc:
            self._show_error(exc)
        finally:
            self._set_busy(False)

    def run_demo(self) -> None:
        try:
            self._set_busy(True)
            self._ensure_pdf_dependency()
            paths = run_aerospace_demo(_project_root())
            self.folder_var.set(str(paths["controlled_folder"]))
            self.database_var.set(str(paths["database"]))
            self.txt_report_var.set(str(paths["txt_report"]))
            self.pdf_report_var.set(str(paths["pdf_report"]))
            self.export_txt_var.set(True)
            self.export_pdf_var.set(True)

            self.status_var.set("Демо выполнено: создан пример с новым, измененным и удаленным файлом.")
            self._log(
                "Демонстрация ORBIS-2 выполнена.\n"
                f"Рабочая папка: {paths['controlled_folder']}\n"
                f"База хэшей: {paths['database']}\n"
                f"TXT-отчет: {paths['txt_report']}\n"
                f"PDF-отчет: {paths['pdf_report']}"
            )
            messagebox.showinfo("Демо выполнено", "Отчеты сохранены в examples/results.")
        except Exception as exc:
            self._show_error(exc)
        finally:
            self._set_busy(False)

    def clear_log(self) -> None:
        self.log.delete("1.0", tk.END)

    def _ensure_pdf_dependency(self) -> None:
        if _reportlab_available():
            return

        install = messagebox.askyesno(
            "Нужна зависимость",
            "Для PDF-отчета нужна библиотека reportlab. Установить ее сейчас?",
        )
        if not install:
            raise RuntimeError(
                "PDF-отчет не создан. Запустите install_requirements.bat "
                "или выполните: python -m pip install -r requirements.txt"
            )

        self.status_var.set("Устанавливаю reportlab для PDF-отчета...")
        self._log("Reportlab не найден. Запускаю установку зависимостей из requirements.txt.")
        self.root.update_idletasks()

        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(_project_root() / "requirements.txt"),
            "--disable-pip-version-check",
        ]
        result = subprocess.run(
            command,
            cwd=str(_project_root()),
            capture_output=True,
            text=True,
        )

        if result.stdout.strip():
            self._log(result.stdout.strip())
        if result.stderr.strip():
            self._log(result.stderr.strip())

        if result.returncode != 0 or not _reportlab_available():
            raise RuntimeError(
                "Не удалось автоматически установить reportlab. "
                "Запустите install_requirements.bat или выполните: "
                "python -m pip install -r requirements.txt"
            )

        self._log("Reportlab установлен, можно создавать PDF-отчет.")

    def _show_error(self, exc: Exception) -> None:
        message = str(exc)
        self.status_var.set(f"Ошибка: {message}")
        self._log(f"Ошибка: {message}")
        messagebox.showerror("Ошибка", message)


def run_gui() -> int:
    root = tk.Tk()
    IntegrityControlApp(root)
    root.mainloop()
    return 0
