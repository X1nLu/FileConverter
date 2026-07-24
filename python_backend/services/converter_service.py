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
# Note: only extensions the converters can actually read are listed.
# openpyxl cannot read .xls and python-docx cannot read .doc.
EXT_VALID_MAP = {
    "pdf": {".pdf"},
    "xlsx": {".xlsx"},
    "docx": {".docx"},
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


def get_formats() -> dict:
    """Return supported format list and source->targets conversion map."""
    formats: list[dict] = []
    seen: set[str] = set()
    conversions: dict[str, list[str]] = {}
    for src, dst in get_supported_conversions():
        conversions.setdefault(src, []).append(dst)
        for ext in (src, dst):
            if ext not in seen:
                seen.add(ext)
                formats.append({"ext": ext, "label": EXT_DESC_MAP.get(ext, ext.upper())})
    return {"formats": formats, "conversions": conversions}


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


def _unique_output_path(output_dir: str, stem: str, to_ext: str) -> str:
    """Generate a non-conflicting output path by appending _1, _2, ... if needed."""
    candidate = Path(output_dir) / f"{stem}.{to_ext}"
    counter = 1
    while candidate.exists():
        candidate = Path(output_dir) / f"{stem}_{counter}.{to_ext}"
        counter += 1
    return str(candidate)


def _make_on_progress(task_id: str):
    """Create an on_progress callback that updates task progress via TaskManager."""
    def on_progress(done: int, total: int):
        task_manager.set_progress_total(task_id, done, total)
    return on_progress


def submit_conversion(
    input_path: str,
    from_ext: str,
    to_ext: str,
    output_dir: str,
    cleanup_input: bool = False,
) -> str:
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
            output_path = _unique_output_path(output_dir, Path(input_path).stem, to_ext)
            on_progress = _make_on_progress(task_id)
            # Report initial progress
            on_progress(0, 1)
            fn(input_path, output_path, on_progress=on_progress)
            task_manager.set_completed(task_id, output_path)
        except Exception as e:
            task_manager.set_failed(task_id, friendly_error(str(e), from_ext))
        finally:
            task_manager.release_slot()
            # Delete the uploaded temp copy (only for /convert uploads,
            # never the user's original file passed via /convert_by_path)
            if cleanup_input:
                try:
                    Path(input_path).unlink(missing_ok=True)
                except OSError:
                    pass

    threading.Thread(target=_run, daemon=True).start()
    return task_id