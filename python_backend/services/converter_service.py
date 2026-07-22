import sys
import os

# Ensure project root converters package is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pathlib import Path
from converters import REGISTRY, get_supported_conversions
from .task_manager import TaskManager

# Global task manager
task_manager = TaskManager()

# Extension validation map per format
EXT_VALID_MAP = {
    "pdf": {".pdf"},
    "xlsx": {".xlsx", ".xls"},
    "docx": {".docx", ".doc"},
    "md": {".md", ".markdown"},
    "zip": {".zip"},
}

# Format description map
EXT_DESC_MAP = {
    "pdf": "PDF",
    "xlsx": "Excel",
    "docx": "Word",
    "md": "Markdown",
    "zip": "ZIP",
}

# Friendly error message map
ERROR_MESSAGES = [
    ("zipfile.BadZipFile", "ZIP file is corrupted"),
    ("is not a zip file", "ZIP file is corrupted"),
    ("No such file", "File not found or has been moved"),
    ("Permission denied", "File is in use, cannot read"),
    ("find_html_file", "No HTML file found in ZIP"),
    ("pdfplumber.open", "PDF file is corrupted or unreadable"),
    ("load_workbook", "Excel file is corrupted or unreadable"),
    ("python-docx", "Word file is corrupted or unreadable"),
    ("Word.Application", "PDF export requires Microsoft Word"),
    ("win32com", "PDF export requires Microsoft Word"),
    ("libreoffice", "PDF export requires LibreOffice"),
]


def get_formats() -> list[dict]:
    """Return supported conversion format list."""
    result = []
    seen = set()
    for src, dst in get_supported_conversions():
        if src not in seen:
            result.append({"ext": src, "label": EXT_DESC_MAP.get(src, src.upper())})
            seen.add(src)
        result.append({"ext": dst, "label": EXT_DESC_MAP.get(dst, dst.upper())})
    # Deduplicate
    unique = []
    seen2 = set()
    for item in result:
        key = item["ext"]
        if key not in seen2:
            seen2.add(key)
            unique.append(item)
    return unique


def friendly_error(raw: str, from_ext: str) -> str:
    """Convert Python exception to user-friendly error message."""
    for keyword, msg in ERROR_MESSAGES:
        if keyword.lower() in raw.lower():
            return msg
    fallback = {
        "pdf": "PDF file cannot be read, may be corrupted",
        "xlsx": "Excel file cannot be read, may be corrupted",
        "docx": "Word file cannot be read, may be corrupted",
        "md": "Markdown file cannot be read",
        "zip": "ZIP file cannot be read, may be corrupted",
    }
    return fallback.get(from_ext, "File cannot be read, may be corrupted")


def submit_conversion(input_path: str, from_ext: str, to_ext: str, output_dir: str) -> str:
    """Submit a conversion task, returns task_id."""
    fn = REGISTRY.get((from_ext, to_ext))
    if fn is None:
        raise ValueError(f"Unsupported conversion: {from_ext} -> {to_ext}")

    # Verify input file exists
    if not Path(input_path).exists():
        raise FileNotFoundError(f"File does not exist: {input_path}")

    # Verify file extension matches source format
    input_suffix = Path(input_path).suffix.lower()
    allowed_exts = EXT_VALID_MAP.get(from_ext)
    if allowed_exts and input_suffix not in allowed_exts:
        raise ValueError(
            f"Extension mismatch: format '{EXT_DESC_MAP.get(from_ext, from_ext.upper())}' "
            f"does not support '{input_suffix}' files"
        )

    task_id = task_manager.create_task(total=1)

    # Attempt to acquire concurrency slot
    if not task_manager.acquire_slot():
        task_manager.set_failed(task_id, "System busy, please try again later")
        return task_id

    import threading

    def _run():
        try:
            task_manager.set_running(task_id)
            output_path = str(Path(output_dir) / f"{Path(input_path).stem}.{to_ext}")
            task_manager.set_progress(task_id, 0)
            fn(input_path, output_path)
            task_manager.set_completed(task_id, output_path)
        except Exception as e:
            task_manager.set_failed(task_id, friendly_error(str(e), from_ext))
        finally:
            task_manager.release_slot()

    threading.Thread(target=_run, daemon=True).start()
    return task_id