import os
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
}


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("文件格式转换工具")
        self.geometry("700x550")
        self.minsize(600, 450)

        self.file_list = []
        self.output_dir = Path.cwd() / "output"

        self._setup_ui()
        self._update_to_options()

    def _setup_ui(self):
        # 输出目录
        dir_frame = ttk.Frame(self)
        dir_frame.pack(fill="x", padx=10, pady=(10, 0))
        ttk.Label(dir_frame, text="输出目录:").pack(side="left")
        self.dir_label = ttk.Label(dir_frame, text=str(self.output_dir), foreground="#555")
        self.dir_label.pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(dir_frame, text="浏览...", command=self._choose_output_dir).pack(side="right")

        # 转换设置
        conv_frame = ttk.LabelFrame(self, text="转换设置", padding=10)
        conv_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(conv_frame, text="从:").grid(row=0, column=0, padx=5, pady=5)
        self.cb_from = ttk.Combobox(conv_frame, values=sorted(FILE_EXT_MAP.keys()), state="readonly", width=12)
        self.cb_from.current(0)
        self.cb_from.bind("<<ComboboxSelected>>", lambda e: self._update_to_options())
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

        ttk.Button(btn_frame, text="添加文件", command=self._add_files).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="移除选中", command=self._remove_selected).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="清空列表", command=self._clear_files).pack(side="left", padx=2)

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

    def _choose_output_dir(self):
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            self.output_dir = Path(d)
            self.dir_label.config(text=str(self.output_dir))

    def _add_files(self):
        from_ext = FILE_EXT_MAP[self.cb_from.get()]
        files = filedialog.askopenfilenames(
            title="选择文件",
            filetypes=[(f"{from_ext.upper()}文件", f"*.{from_ext}"), ("所有文件", "*.*")]
        )
        for path in files:
            f = Path(path)
            if f not in self.file_list:
                self.file_list.append(f)
                self.listbox.insert("end", f"{f.name}  ({f.parent})")
        self._update_file_count()

    def _clear_files(self):
        self.file_list.clear()
        self.listbox.delete(0, "end")
        self._update_file_count()

    def _remove_selected(self):
        for sel in reversed(self.listbox.curselection()):
            self.listbox.delete(sel)
            self.file_list.pop(sel)
        self._update_file_count()

    def _update_file_count(self):
        self.file_count_label.config(text=f"共 {len(self.file_list)} 个文件")

    def _start_conversion(self):
        if not self.file_list:
            messagebox.showwarning("提示", "请先添加文件")
            return

        from_ext = FILE_EXT_MAP[self.cb_from.get()]
        to_ext = FILE_EXT_MAP[self.cb_to.get()]
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.btn_convert.config(state="disabled", text="转换中...")
        self.progress["value"] = 0
        self.progress_label.config(text="")

        files = self.file_list.copy()
        t = threading.Thread(target=self._run_conversion, args=(files, from_ext, to_ext), daemon=True)
        t.start()

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
            except Exception as e:
                failed.append((f.name, str(e)))
        self.after(0, lambda: self._on_conversion_finished(failed, total))

    def _update_progress(self, current, total):
        self.progress["maximum"] = total
        self.progress["value"] = current
        self.progress_label.config(text=f"正在转换: {current}/{total}")

    def _on_conversion_finished(self, failed, total):
        self.progress["value"] = total
        if failed:
            self.progress_label.config(text=f"已完成，{len(failed)} 个文件失败")
            failed_names = "\n".join(f"{name}: {msg}" for name, msg in failed[:5])
            summary = (
                f"{total - len(failed)} 个文件转换成功，{len(failed)} 个文件转换失败。\n\n"
                f"失败示例：\n{failed_names}"
            )
            messagebox.showwarning("部分完成", summary)
        else:
            self.progress_label.config(text="转换完成！")
            messagebox.showinfo("完成", "所有文件转换完成！")
        self._reset_convert_button()

    def _reset_convert_button(self):
        self.btn_convert.config(state="normal", text="开始转换")