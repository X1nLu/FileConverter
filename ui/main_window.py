import os
import re
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from converters import REGISTRY, get_supported_conversions

FILE_EXT_MAP = {
    "PDF": "pdf",
    "Excel": "xlsx",
    "Word": "docx",
    "Markdown": "md",
    "ZIP (HTML→MD)": "zip",
}

# 格式对应的扩展名校验集合（添加文件时严格匹配）
EXT_VALID_MAP = {
    "pdf": {".pdf"},
    "xlsx": {".xlsx", ".xls"},
    "docx": {".docx", ".doc"},
    "md": {".md", ".markdown"},
    "zip": {".zip"},
}

# 格式对应的中文描述
EXT_DESC_MAP = {
    "pdf": "PDF",
    "xlsx": "Excel",
    "docx": "Word",
    "md": "Markdown",
    "zip": "ZIP",
}

# 友好错误消息映射
ERROR_MESSAGES = [
    ("zipfile.BadZipFile", "ZIP 文件已损坏"),
    ("is not a zip file", "ZIP 文件已损坏"),
    ("No such file", "文件不存在或已被移动"),
    ("Permission denied", "文件被占用，无法读取"),
    ("find_html_file", "ZIP 中未找到 HTML 文件"),
    ("pdfplumber.open", "PDF 文件已损坏或无法解析"),
    ("load_workbook", "Excel 文件已损坏或无法解析"),
    ("python-docx", "Word 文件已损坏或无法解析"),
    ("Word.Application", "→PDF 需安装 Microsoft Word"),
    ("win32com", "→PDF 需安装 Microsoft Word"),
    ("libreoffice", "→PDF 需安装 LibreOffice"),
]


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("文件格式转换工具")
        self.geometry("700x550")
        self.minsize(650, 500)

        self.file_list = []       # List[Path]
        self.file_status = {}     # {Path: "ok" | "error"}
        self.output_dir = Path.cwd() / "output"

        self._setup_ui()
        self._update_to_options()

    # ------------------------------------------------------------------ #
    #  UI 搭建
    # ------------------------------------------------------------------ #

    def _setup_ui(self):
        # 输出目录
        dir_frame = ttk.Frame(self)
        dir_frame.pack(fill="x", padx=10, pady=(10, 0))
        ttk.Label(dir_frame, text="输出目录:").pack(side="left")
        self.dir_label = ttk.Label(dir_frame, text=str(self.output_dir), foreground="#555")
        self.dir_label.pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(dir_frame, text="浏览...", command=self._choose_output_dir).pack(side="right")
        ttk.Button(dir_frame, text="打开输出目录", command=self._open_output_dir).pack(side="right", padx=(0, 8))

        # 转换设置
        conv_frame = ttk.LabelFrame(self, text="转换设置", padding=10)
        conv_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(conv_frame, text="从:").grid(row=0, column=0, padx=5, pady=5)
        self.cb_from = ttk.Combobox(conv_frame, values=sorted(FILE_EXT_MAP.keys()), state="readonly", width=12)
        self.cb_from.current(0)
        self.cb_from.bind("<<ComboboxSelected>>", lambda e: self._on_from_changed())
        self.cb_from.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(conv_frame, text="→").grid(row=0, column=2, padx=5, pady=5)
        self.cb_to = ttk.Combobox(conv_frame, state="readonly", width=12)
        self.cb_to.grid(row=0, column=3, padx=5, pady=5)

        # 文件列表
        file_frame = ttk.LabelFrame(self, text="文件列表", padding=5)
        file_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(list_frame, selectmode="extended", yscrollcommand=scrollbar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)

        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill="x", pady=(5, 0))

        self.file_count_label = ttk.Label(btn_frame, text="共 0 个文件")
        self.file_count_label.pack(side="left", padx=5)

        self.btn_add = ttk.Button(btn_frame, text="添加文件", command=self._add_files)
        self.btn_add.pack(side="left", padx=2)
        self.btn_remove = ttk.Button(btn_frame, text="移除选中", command=self._remove_selected)
        self.btn_remove.pack(side="left", padx=2)
        self.btn_clear = ttk.Button(btn_frame, text="清空列表", command=self._clear_files)
        self.btn_clear.pack(side="left", padx=2)

        # 进度条
        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=(0, 10))
        self.progress_label = ttk.Label(self, text="", foreground="#555")
        self.progress_label.pack(padx=10)

        # 转换按钮
        self.btn_convert = tk.Button(
            self, text="开始转换", command=self._start_conversion,
            bg="#1890ff", fg="white", font=("", 12, "bold"),
            relief="flat", padx=20, pady=5,
            activebackground="#40a9ff", activeforeground="white",
        )
        self.btn_convert.pack(pady=(0, 10))
        self.btn_convert.bind("<Enter>", lambda e: self.btn_convert.config(bg="#40a9ff"))
        self.btn_convert.bind("<Leave>", lambda e: self.btn_convert.config(bg="#1890ff"))

    # ------------------------------------------------------------------ #
    #  下拉框联动
    # ------------------------------------------------------------------ #

    def _update_to_options(self):
        from_ext = FILE_EXT_MAP[self.cb_from.get()]
        self.cb_to.set("")
        options = []
        for src, dst in get_supported_conversions():
            if src == from_ext:
                label = [k for k, v in FILE_EXT_MAP.items() if v == dst][0]
                options.append(label)
        self.cb_to.config(values=options)
        if options:
            self.cb_to.current(0)

    def _on_from_changed(self):
        """来源格式切换时：更新目标选项 + 刷新文件列表状态标记。"""
        self._update_to_options()
        self._refresh_file_list_display()

    # ------------------------------------------------------------------ #
    #  输出目录
    # ------------------------------------------------------------------ #

    def _choose_output_dir(self):
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            self.output_dir = Path(d)
            self.dir_label.config(text=str(self.output_dir))

    def _open_output_dir(self):
        if not self.output_dir.exists():
            messagebox.showwarning("提示", "输出目录不存在，请先执行一次转换或手动创建目录")
            return
        try:
            os.startfile(self.output_dir)
        except Exception as exc:
            messagebox.showerror("打开失败", f"无法打开输出目录：{exc}")

    def _resolve_format_for_extension(self, ext: str) -> str | None:
        for fmt, valid_exts in EXT_VALID_MAP.items():
            if ext in valid_exts:
                return fmt
        return None

    def _resolve_source_label(self, fmt: str) -> str | None:
        return next((k for k, v in FILE_EXT_MAP.items() if v == fmt), None)

    def _resolve_paths_format(self, paths: list[str]) -> str | None:
        candidate_format = None
        for path in paths:
            ext = Path(path).suffix.lower()
            fmt = self._resolve_format_for_extension(ext)
            if fmt is None:
                return None
            if candidate_format is None:
                candidate_format = fmt
            elif candidate_format != fmt:
                return None
        return candidate_format

    def _current_list_format(self) -> str | None:
        if not self.file_list:
            return None
        formats = {self._resolve_format_for_extension(f.suffix.lower()) for f in self.file_list}
        if None in formats or len(formats) != 1:
            return None
        return next(iter(formats))

    def _switch_source_format(self, candidate_format: str) -> None:
        target_label = self._resolve_source_label(candidate_format)
        if target_label and self.cb_from.get() != target_label:
            self.cb_from.set(target_label)
            self._update_to_options()

    def _filter_paths_by_format(self, paths: list[str], fmt: str) -> tuple[list[Path], list[str]]:
        valid_exts = EXT_VALID_MAP.get(fmt, {f".{fmt}"})
        accepted: list[Path] = []
        rejected: list[str] = []
        for path in paths:
            f = Path(path)
            if f.suffix.lower() in valid_exts:
                accepted.append(f)
            else:
                rejected.append(f.name)
        return accepted, rejected

    def _append_files(self, files: list[Path]) -> int:
        added = 0
        for f in files:
            if f not in self.file_list:
                self.file_list.append(f)
                self.file_status[f] = "ok"
                added += 1
        return added

    def _show_rejected_files(self, rejected: list[str], desc: str) -> None:
        if not rejected:
            return
        msg = "\n".join(rejected[:5])
        suffix = f"\n……及其他 {len(rejected) - 5} 个" if len(rejected) > 5 else ""
        messagebox.showwarning(
            "文件格式不匹配",
            f"以下文件不是 {desc} 格式，已跳过：\n\n{msg}{suffix}"
        )

    def _prepare_paths_for_add(self, paths: list[str], action_name: str) -> str | None:
        candidate_format = self._resolve_paths_format(paths)
        if candidate_format is None:
            messagebox.showwarning(
                "文件格式不一致",
                f"{action_name}的文件包含多种格式或不支持的格式，请先统一格式后再操作。"
            )
            return None

        existing_format = self._current_list_format()
        if existing_format is not None and existing_format != candidate_format:
            messagebox.showwarning(
                "文件列表不一致",
                "当前文件列表中已有不同格式的文件，请先清空列表或统一格式后再操作。"
            )
            return None

        self._switch_source_format(candidate_format)
        return candidate_format

    # ------------------------------------------------------------------ #
    #  文件管理（含严格扩展名校验）
    # ------------------------------------------------------------------ #

    def _add_files(self):
        files = filedialog.askopenfilenames(
            title="选择文件",
            filetypes=[(f"{EXT_DESC_MAP.get(FILE_EXT_MAP[self.cb_from.get()], self.cb_from.get())}文件", f"*.{FILE_EXT_MAP[self.cb_from.get()]}",), ("所有文件", "*.*")]
        )

        if not files:
            return

        candidate_format = self._prepare_paths_for_add(files, "选择")
        if candidate_format is None:
            return

        accepted, rejected = self._filter_paths_by_format(files, candidate_format)
        desc = EXT_DESC_MAP.get(candidate_format, candidate_format.upper())
        added = self._append_files(accepted)
        self._show_rejected_files(rejected, desc)
        if added > 0:
            self._refresh_file_list_display()

    def _clear_files(self):
        self.file_list.clear()
        self.file_status.clear()
        self.listbox.delete(0, "end")
        self._update_file_count()

    def _remove_selected(self):
        for sel in reversed(self.listbox.curselection()):
            self.listbox.delete(sel)
            removed = self.file_list.pop(sel)
            self.file_status.pop(removed, None)
        self._update_file_count()

    def _update_file_count(self):
        self.file_count_label.config(text=f"共 {len(self.file_list)} 个文件")

    def _refresh_file_list_display(self):
        """刷新文件列表显示（含状态标记）。"""
        self.listbox.delete(0, "end")
        for f in self.file_list:
            status = self.file_status.get(f, "ok")
            prefix = "✅" if status == "ok" else "❌"
            self.listbox.insert("end", f"{prefix}  {f.name}  ({f.parent})")
        self._update_file_count()

    # ------------------------------------------------------------------ #
    #  转换前预检
    # ------------------------------------------------------------------ #

    def _start_conversion(self):
        if not self.file_list:
            messagebox.showwarning("提示", "请先添加文件")
            return

        if not self.cb_to.get():
            messagebox.showwarning("提示", "请选择目标格式")
            return

        from_ext = FILE_EXT_MAP[self.cb_from.get()]
        to_ext = FILE_EXT_MAP.get(self.cb_to.get())
        if not to_ext:
            messagebox.showerror("转换失败", "目标格式无效，请重新选择")
            return

        # 预检：文件是否存在
        missing = [f.name for f in self.file_list if not f.exists()]
        if missing:
            msg = "\n".join(missing[:5])
            messagebox.showerror("文件不存在", f"以下文件不存在或已被移动：\n\n{msg}")
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)

        fn = REGISTRY.get((from_ext, to_ext))
        if fn is None:
            messagebox.showerror("转换失败", f"不支持 {from_ext.upper()} → {to_ext.upper()} 的转换")
            return

        self.btn_convert.config(state="disabled", text="转换中...")
        self.btn_add.config(state="disabled")
        self.btn_remove.config(state="disabled")
        self.btn_clear.config(state="disabled")
        self.progress["value"] = 0
        self.progress_label.config(text="")

        files = self.file_list.copy()
        t = threading.Thread(target=self._run_conversion, args=(files, from_ext, to_ext), daemon=True)
        t.start()

    # ------------------------------------------------------------------ #
    #  转换执行
    # ------------------------------------------------------------------ #

    def _run_conversion(self, files, from_ext, to_ext):
        total = len(files)
        failed = []
        fn = REGISTRY.get((from_ext, to_ext))

        for idx, f in enumerate(files, start=1):
            output_path = str(self.output_dir / f"{f.stem}.{to_ext}")
            self.after(0, lambda current=idx, total=total: self._update_progress(current, total))
            try:
                if fn:
                    fn(str(f), output_path)
                self.file_status[f] = "ok"
            except Exception as e:
                friendly = self._friendly_error(str(e), from_ext)
                failed.append((f.name, friendly))
                self.file_status[f] = "error"

        self.after(0, lambda: self._on_conversion_finished(failed, total))

    def _update_progress(self, current, total):
        self.progress["maximum"] = total
        self.progress["value"] = current
        self.progress_label.config(text=f"正在转换: {current}/{total}")

    # ------------------------------------------------------------------ #
    #  错误处理
    # ------------------------------------------------------------------ #

    @staticmethod
    def _friendly_error(raw: str, from_ext: str) -> str:
        """将 Python 异常转为友好的中文提示。"""
        for keyword, msg in ERROR_MESSAGES:
            if keyword.lower() in raw.lower():
                return msg
        # 按格式兜底
        fallback = {
            "pdf": "PDF 文件无法读取，可能已损坏",
            "xlsx": "Excel 文件无法读取，可能已损坏",
            "docx": "Word 文件无法读取，可能已损坏",
            "md": "Markdown 文件无法读取",
            "zip": "ZIP 文件无法读取，可能已损坏",
        }
        return fallback.get(from_ext, "文件无法读取，可能已损坏")

    def _on_conversion_finished(self, failed, total):
        self.progress["value"] = total
        self._refresh_file_list_display()

        if failed:
            self.progress_label.config(text=f"已完成，{len(failed)} 个文件失败")
            failed_names = "\n".join(f"❌ {name}：{msg}" for name, msg in failed[:5])
            summary = (
                f"{total - len(failed)} 个文件转换成功，{len(failed)} 个文件转换失败\n\n"
                f"{failed_names}"
            )
            messagebox.showwarning("转换结果", summary)
        else:
            self.progress_label.config(text="转换完成！")
            messagebox.showinfo("转换结果", f"全部 {total} 个文件转换成功")
        self._reset_convert_button()

    def _reset_convert_button(self):
        self.btn_convert.config(state="normal", text="开始转换")
        self.btn_add.config(state="normal")
        self.btn_remove.config(state="normal")
        self.btn_clear.config(state="normal")