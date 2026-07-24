"""Tests for converter_service — submit_conversion, error handling."""

import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
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


if __name__ == "__main__":
    unittest.main()