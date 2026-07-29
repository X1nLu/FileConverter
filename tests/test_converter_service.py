"""Tests for converter_service — submit_conversion, error handling."""

import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from unittest.mock import patch
from python_backend.services.converter_service import (
    submit_conversion,
    friendly_error,
    get_formats,
    task_manager,
)


class TestSubmitConversion(unittest.TestCase):
    """Test submit_conversion workflow."""

    def setUp(self):
        # Create a sample PDF
        self.tmpdir = tempfile.TemporaryDirectory()
        self.pdf_path = os.path.join(self.tmpdir.name, "sample.pdf")
        from tests.test_converters import _make_sample_pdf
        _make_sample_pdf(self.pdf_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_submit_success(self):
        """Submit a valid conversion and wait for completion."""
        task_id = submit_conversion(
            input_path=self.pdf_path,
            from_ext="pdf",
            to_ext="md",
            output_dir=self.tmpdir.name,
        )
        # Wait for completion
        for _ in range(50):
            task = task_manager.get_task(task_id)
            if task and task.status in ("completed", "failed"):
                break
            time.sleep(0.05)
        task = task_manager.get_task(task_id)
        self.assertIsNotNone(task)
        self.assertEqual(
            task.status, "completed",
            f"Expected completed, got {task.status}: {task.error}",
        )
        self.assertIsNotNone(task.result)
        self.assertTrue(os.path.isfile(task.result))

    def test_submit_unsupported(self):
        """Unsupported conversion raises ValueError."""
        with self.assertRaises(ValueError):
            submit_conversion(
                input_path=self.pdf_path,
                from_ext="pdf",
                to_ext="zip",
                output_dir=self.tmpdir.name,
            )

    def test_submit_file_not_found(self):
        """Non-existent file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            submit_conversion(
                input_path="/nonexistent/file.pdf",
                from_ext="pdf",
                to_ext="md",
                output_dir=self.tmpdir.name,
            )

    def test_submit_extension_mismatch(self):
        """Extension mismatch raises ValueError."""
        with self.assertRaises(ValueError):
            submit_conversion(
                input_path=self.pdf_path,
                from_ext="xlsx",  # Wrong: file is PDF
                to_ext="md",
                output_dir=self.tmpdir.name,
            )


class TestFriendlyError(unittest.TestCase):
    """Test friendly_error mapping."""

    def test_zipfile_error(self):
        msg = friendly_error("zipfile.BadZipFile: file is not a zip file", "zip")
        self.assertIn("corrupted", msg.lower())

    def test_filenotfound(self):
        msg = friendly_error("No such file or directory: /x", "pdf")
        self.assertIn("not found", msg.lower())

    def test_fallback_pdf(self):
        msg = friendly_error("Some random error", "pdf")
        self.assertIn("corrupted", msg.lower())

    def test_fallback_unknown(self):
        msg = friendly_error("Some random error", "unknown")
        self.assertIn("cannot be read", msg.lower())


class TestGetFormats(unittest.TestCase):
    """Test get_formats returns expected structure."""

    def test_formats_structure(self):
        data = get_formats()
        self.assertIn("formats", data)
        self.assertIn("conversions", data)
        self.assertGreater(len(data["formats"]), 0)
        self.assertGreater(len(data["conversions"]), 0)

    def test_conversions_count(self):
        data = get_formats()
        total = sum(len(v) for v in data["conversions"].values())
        self.assertEqual(total, 13, f"Expected 13 conversion entries, got {total}")


class TestCleanupInput(unittest.TestCase):
    """Test cleanup_input parameter in submit_conversion."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.pdf_path = os.path.join(self.tmpdir.name, "sample.pdf")
        from tests.test_converters import _make_sample_pdf
        _make_sample_pdf(self.pdf_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_cleanup_input_true_deletes_file(self):
        """When cleanup_input=True, the input file should be deleted after conversion."""
        # Copy the file so we can check if it's deleted
        import shutil
        copy_path = os.path.join(self.tmpdir.name, "copy.pdf")
        shutil.copy2(self.pdf_path, copy_path)
        self.assertTrue(os.path.isfile(copy_path))

        task_id = submit_conversion(
            input_path=copy_path,
            from_ext="pdf",
            to_ext="md",
            output_dir=self.tmpdir.name,
            cleanup_input=True,
        )
        # Wait for completion
        for _ in range(50):
            task = task_manager.get_task(task_id)
            if task and task.status in ("completed", "failed"):
                break
            time.sleep(0.05)
        task = task_manager.get_task(task_id)
        self.assertEqual(task.status, "completed")
        # Input file should be deleted
        self.assertFalse(os.path.isfile(copy_path),
                         "Input file should be deleted when cleanup_input=True")

    def test_cleanup_input_false_keeps_file(self):
        """When cleanup_input=False, the input file should remain after conversion."""
        task_id = submit_conversion(
            input_path=self.pdf_path,
            from_ext="pdf",
            to_ext="md",
            output_dir=self.tmpdir.name,
            cleanup_input=False,
        )
        for _ in range(50):
            task = task_manager.get_task(task_id)
            if task and task.status in ("completed", "failed"):
                break
            time.sleep(0.05)
        task = task_manager.get_task(task_id)
        self.assertEqual(task.status, "completed")
        # Input file should still exist
        self.assertTrue(os.path.isfile(self.pdf_path),
                        "Input file should remain when cleanup_input=False")

    def test_cleanup_input_default_false(self):
        """Default cleanup_input should be False (keep file)."""
        task_id = submit_conversion(
            input_path=self.pdf_path,
            from_ext="pdf",
            to_ext="md",
            output_dir=self.tmpdir.name,
        )
        for _ in range(50):
            task = task_manager.get_task(task_id)
            if task and task.status in ("completed", "failed"):
                break
            time.sleep(0.05)
        task = task_manager.get_task(task_id)
        self.assertEqual(task.status, "completed")
        self.assertTrue(os.path.isfile(self.pdf_path),
                        "Input file should remain by default")


class TestUniqueOutputPath(unittest.TestCase):
    """Test _unique_output_path generates non-conflicting paths."""

    def test_unique_output_path_no_conflict(self):
        """When no file exists, should return the base path."""
        from python_backend.services.converter_service import _unique_output_path
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _unique_output_path(tmpdir, "output", "md")
            expected = os.path.join(tmpdir, "output.md")
            self.assertEqual(result, expected)

    def test_unique_output_path_with_conflict(self):
        """When file exists, should append _1, _2, etc."""
        from python_backend.services.converter_service import _unique_output_path
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create existing file
            Path(os.path.join(tmpdir, "output.md")).touch()
            result = _unique_output_path(tmpdir, "output", "md")
            expected = os.path.join(tmpdir, "output_1.md")
            self.assertEqual(result, expected)

    def test_unique_output_path_multiple_conflicts(self):
        """When multiple files exist, should increment counter."""
        from python_backend.services.converter_service import _unique_output_path
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(os.path.join(tmpdir, "output.md")).touch()
            Path(os.path.join(tmpdir, "output_1.md")).touch()
            result = _unique_output_path(tmpdir, "output", "md")
            expected = os.path.join(tmpdir, "output_2.md")
            self.assertEqual(result, expected)


class TestFriendlyErrorExtended(unittest.TestCase):
    """Extended tests for friendly_error mapping."""

    def test_permission_denied(self):
        msg = friendly_error("Permission denied: /path/to/file", "pdf")
        self.assertIn("in use", msg.lower())

    def test_pdfplumber_error(self):
        msg = friendly_error("pdfplumber.open: cannot read PDF", "pdf")
        self.assertIn("corrupted", msg.lower())

    def test_load_workbook_error(self):
        msg = friendly_error("load_workbook: file is corrupted", "xlsx")
        self.assertIn("corrupted", msg.lower())

    def test_python_docx_error(self):
        msg = friendly_error("python-docx: error reading document", "docx")
        self.assertIn("corrupted", msg.lower())

    def test_libreoffice_error(self):
        msg = friendly_error("libreoffice: conversion failed", "docx")
        self.assertIn("libreoffice", msg.lower())

    def test_win32com_error(self):
        msg = friendly_error("win32com: COM error", "docx")
        self.assertIn("microsoft word", msg.lower())

    def test_fallback_xlsx(self):
        msg = friendly_error("Some random error", "xlsx")
        self.assertIn("corrupted", msg.lower())

    def test_fallback_docx(self):
        msg = friendly_error("Some random error", "docx")
        self.assertIn("corrupted", msg.lower())

    def test_fallback_md(self):
        msg = friendly_error("Some random error", "md")
        self.assertIn("cannot be read", msg.lower())

    def test_fallback_zip(self):
        msg = friendly_error("Some random error", "zip")
        self.assertIn("corrupted", msg.lower())

    def test_find_html_file_error(self):
        msg = friendly_error("find_html_file: no HTML found", "zip")
        self.assertIn("html", msg.lower())

    def test_case_insensitive_matching(self):
        """Keyword matching should be case-insensitive."""
        msg = friendly_error("NO SUCH FILE: /x", "pdf")
        self.assertIn("not found", msg.lower())


class TestSubmitConversionExtended(unittest.TestCase):
    """Extended tests for submit_conversion edge cases."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.pdf_path = os.path.join(self.tmpdir.name, "sample.pdf")
        from tests.test_converters import _make_sample_pdf
        _make_sample_pdf(self.pdf_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_submit_system_busy(self):
        """When all concurrency slots are full, task should fail with 'System busy'."""
        # Acquire all 4 slots
        from python_backend.services.converter_service import task_manager as tm
        acquired = []
        for _ in range(4):
            acquired.append(tm.acquire_slot())
        self.assertTrue(all(acquired))

        try:
            task_id = submit_conversion(
                input_path=self.pdf_path,
                from_ext="pdf",
                to_ext="md",
                output_dir=self.tmpdir.name,
            )
            # Wait briefly for the task to be processed
            time.sleep(0.1)
            task = tm.get_task(task_id)
            self.assertIsNotNone(task)
            self.assertEqual(task.status, "failed")
            self.assertIn("busy", task.error.lower())
        finally:
            # Release slots
            for _ in range(4):
                tm.release_slot()

    def test_submit_multiple_formats(self):
        """Submit conversions for all supported source formats."""
        from tests.test_converters import (
            _make_sample_pdf, _make_sample_xlsx,
            _make_sample_docx, _make_sample_md,
        )

        test_cases = [
            ("pdf", "md", _make_sample_pdf),
            ("xlsx", "md", _make_sample_xlsx),
            ("docx", "md", _make_sample_docx),
            ("md", "pdf", _make_sample_md),
        ]

        for from_ext, to_ext, maker in test_cases:
            with self.subTest(f"{from_ext} -> {to_ext}"):
                src = os.path.join(self.tmpdir.name, f"sample.{from_ext}")
                maker(src)
                task_id = submit_conversion(
                    input_path=src,
                    from_ext=from_ext,
                    to_ext=to_ext,
                    output_dir=self.tmpdir.name,
                )
                for _ in range(50):
                    task = task_manager.get_task(task_id)
                    if task and task.status in ("completed", "failed"):
                        break
                    time.sleep(0.05)
                task = task_manager.get_task(task_id)
                self.assertEqual(
                    task.status, "completed",
                    f"{from_ext} -> {to_ext}: expected completed, got {task.status}: {task.error}",
                )

    def test_submit_timeout(self):
        """A conversion that exceeds timeout should be marked as failed."""
        import python_backend.services.converter_service as cs

        src = os.path.join(self.tmpdir.name, "slow.md")
        Path(src).write_text("hello", encoding="utf-8")

        def slow_converter(input_path, output_path, on_progress=None):
            time.sleep(0.2)
            Path(output_path).write_text("done", encoding="utf-8")

        key = ("md", "md")
        old = cs.REGISTRY.get(key)
        cs.REGISTRY[key] = slow_converter
        try:
            with patch.object(cs, "CONVERSION_TIMEOUT_SECONDS", 0.05):
                task_id = submit_conversion(
                    input_path=src,
                    from_ext="md",
                    to_ext="md",
                    output_dir=self.tmpdir.name,
                )
                for _ in range(50):
                    task = task_manager.get_task(task_id)
                    if task and task.status in ("completed", "failed"):
                        break
                    time.sleep(0.02)
                task = task_manager.get_task(task_id)
                self.assertIsNotNone(task)
                self.assertEqual(task.status, "failed")
                self.assertIn("timed out", (task.error or "").lower())
        finally:
            if old is None:
                del cs.REGISTRY[key]
            else:
                cs.REGISTRY[key] = old


if __name__ == "__main__":
    unittest.main()