import sys
import os

# 确保能找到项目根目录的 converters 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pathlib import Path
from converters import REGISTRY, get_supported_conversions
from .task_manager import TaskManager

# 全局任务管理器
task_manager = TaskManager()

# 格式对应的扩展名校验集合（与旧版 Tkinter 一致）
EXT_VALID_MAP = {
    "pdf": {".pdf"},
    "xlsx": {".xlsx", ".xls"},
    "docx": {".docx", ".doc"},
    "md": {".md", ".markdown"},
    "zip": {".zip"},
}

# 格式描述映射
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


def get_formats() -> list[dict]:
    """返回支持的转换格式列表。"""
    result = []
    seen = set()
    for src, dst in get_supported_conversions():
        if src not in seen:
            result.append({"ext": src, "label": EXT_DESC_MAP.get(src, src.upper())})
            seen.add(src)
        result.append({"ext": dst, "label": EXT_DESC_MAP.get(dst, dst.upper())})
    # 去重
    unique = []
    seen2 = set()
    for item in result:
        key = item["ext"]
        if key not in seen2:
            seen2.add(key)
            unique.append(item)
    return unique


def friendly_error(raw: str, from_ext: str) -> str:
    """将 Python 异常转为友好的中文提示。"""
    for keyword, msg in ERROR_MESSAGES:
        if keyword.lower() in raw.lower():
            return msg
    fallback = {
        "pdf": "PDF 文件无法读取，可能已损坏",
        "xlsx": "Excel 文件无法读取，可能已损坏",
        "docx": "Word 文件无法读取，可能已损坏",
        "md": "Markdown 文件无法读取",
        "zip": "ZIP 文件无法读取，可能已损坏",
    }
    return fallback.get(from_ext, "文件无法读取，可能已损坏")


def submit_conversion(input_path: str, from_ext: str, to_ext: str, output_dir: str) -> str:
    """提交一个转换任务，返回 task_id。"""
    fn = REGISTRY.get((from_ext, to_ext))
    if fn is None:
        raise ValueError(f"不支持的转换: {from_ext} -> {to_ext}")

    # 验证输入文件存在
    if not Path(input_path).exists():
        raise FileNotFoundError(f"文件不存在: {input_path}")

    # 验证文件扩展名与来源格式匹配
    input_suffix = Path(input_path).suffix.lower()
    allowed_exts = EXT_VALID_MAP.get(from_ext)
    if allowed_exts and input_suffix not in allowed_exts:
        raise ValueError(
            f"文件扩展名不匹配: 格式 '{EXT_DESC_MAP.get(from_ext, from_ext.upper())}' "
            f"不支持 '{input_suffix}' 文件"
        )

    task_id = task_manager.create_task(total=1)

    # 尝试获取并发槽位
    if not task_manager.acquire_slot():
        task_manager.set_failed(task_id, "系统繁忙，请稍后再试")
        return task_id

    import threading

    def _run():
        try:
            task_manager.set_running(task_id)
            output_path = str(Path(output_dir) / f"{Path(input_path).stem}.{to_ext}")
            print(f"DEBUG: convert output_path={output_path}", flush=True)
            task_manager.set_progress(task_id, 0)
            fn(input_path, output_path)
            task_manager.set_completed(task_id, output_path)
        except Exception as e:
            task_manager.set_failed(task_id, friendly_error(str(e), from_ext))
        finally:
            task_manager.release_slot()

    threading.Thread(target=_run, daemon=True).start()
    return task_id