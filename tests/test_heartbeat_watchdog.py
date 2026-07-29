"""Tests for heartbeat watchdog, stdin listener, port allocation, and API endpoints."""

import os
import sys
import time
import json
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root and python_backend are in path
_project_root = str(Path(__file__).parent.parent)
_python_backend = os.path.join(_project_root, "python_backend")
for p in [_project_root, _python_backend]:
    if p not in sys.path:
        sys.path.insert(0, p)

import unittest


# ── Heartbeat Watchdog Tests ─────────────────────────────────────────

class TestHeartbeatWatchdog(unittest.TestCase):
    """Test the heartbeat watchdog thread behavior."""

    def setUp(self):
        # Create a temp heartbeat file
        self.hb_fd, self.hb_path = tempfile.mkstemp(suffix=".tmp")
        os.close(self.hb_fd)
        # Reset global state that may have been set by other tests
        import python_backend.main as main_mod
        main_mod._shutdown_requested = False

    def tearDown(self):
        try:
            os.unlink(self.hb_path)
        except OSError:
            pass

    def test_watchdog_exits_when_file_stale(self):
        """Watchdog should call os._exit when heartbeat file is not updated within timeout."""
        from python_backend.main import start_heartbeat_watchdog

        exit_called_with = [None]

        def fake_exit(code):
            exit_called_with[0] = code
            raise SystemExit(code)

        with patch.object(os, '_exit', fake_exit):
            start_heartbeat_watchdog(self.hb_path, timeout=0.01, check_interval=0.015)
            # Wait for watchdog to detect stale file
            time.sleep(0.1)

        self.assertIsNotNone(
            exit_called_with[0],
            "os._exit should have been called due to heartbeat timeout",
        )

    def test_watchdog_exits_when_file_lost(self):
        """Watchdog should call os._exit when heartbeat file is deleted."""
        from python_backend.main import start_heartbeat_watchdog

        exit_called_with = [None]

        def fake_exit(code):
            exit_called_with[0] = code
            raise SystemExit(code)

        with patch.object(os, '_exit', fake_exit):
            start_heartbeat_watchdog(self.hb_path, timeout=5.0, check_interval=0.015)
            # Delete the file
            os.unlink(self.hb_path)
            time.sleep(0.1)

        self.assertIsNotNone(
            exit_called_with[0],
            "os._exit should have been called when heartbeat file is lost",
        )

    def test_watchdog_stays_alive_with_updates(self):
        """Watchdog should NOT call os._exit when heartbeat file is regularly updated."""
        from python_backend.main import start_heartbeat_watchdog

        exit_called = [False]

        def fake_exit(code):
            exit_called[0] = True
            raise SystemExit(code)

        with patch.object(os, '_exit', fake_exit):
            start_heartbeat_watchdog(self.hb_path, timeout=0.05, check_interval=0.025)

            # Update the file repeatedly (faster than watchdog sleep)
            for _ in range(3):
                try:
                    os.utime(self.hb_path, None)
                except OSError:
                    pass
                time.sleep(0.01)

            # Give watchdog a chance to check
            time.sleep(0.03)

        self.assertFalse(
            exit_called[0],
            "os._exit should NOT have been called while heartbeat is updated",
        )


# ── Stdin Listener Tests ─────────────────────────────────────────────

class TestStdinListener(unittest.TestCase):
    """Test the stdin listener thread behavior."""

    def test_stdin_listener_starts_daemon_thread(self):
        """stdin listener thread should be daemon and not block."""
        from python_backend.main import start_stdin_listener

        thread_count_before = threading.active_count()
        start_stdin_listener()
        thread_count_after = threading.active_count()

        self.assertEqual(
            thread_count_after, thread_count_before + 1,
            "stdin listener should create a new daemon thread",
        )


# ── Port Allocation Tests ────────────────────────────────────────────

class TestFindFreePort(unittest.TestCase):
    """Test the find_free_port function."""

    def setUp(self):
        self._original_port = os.environ.pop("BACKEND_PORT", None)

    def tearDown(self):
        if self._original_port is not None:
            os.environ["BACKEND_PORT"] = self._original_port
        elif "BACKEND_PORT" in os.environ:
            del os.environ["BACKEND_PORT"]

    def test_find_free_port_returns_valid_port(self):
        from python_backend.main import find_free_port
        port = find_free_port()
        self.assertIsInstance(port, int)
        self.assertGreater(port, 0)
        self.assertLess(port, 65536)

    def test_find_free_port_env_var(self):
        from python_backend.main import find_free_port
        os.environ["BACKEND_PORT"] = "19999"
        port = find_free_port()
        self.assertEqual(port, 19999)

    def test_find_free_port_env_var_invalid(self):
        from python_backend.main import find_free_port
        os.environ["BACKEND_PORT"] = "abc"
        with self.assertRaises(ValueError):
            find_free_port()


# ── API Endpoint Tests ───────────────────────────────────────────────

class TestAPIEndpoints(unittest.TestCase):
    """Test the FastAPI endpoints using TestClient."""

    @classmethod
    def setUpClass(cls):
        from python_backend.main import app
        from fastapi.testclient import TestClient
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        """GET /health should return {'status': 'ok'}."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_heartbeat_endpoint(self):
        """POST /heartbeat should return {'status': 'ok'}."""
        response = self.client.post("/heartbeat")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_heartbeat_updates_file(self):
        """POST /heartbeat should update the heartbeat file mtime."""
        import python_backend.main as main_mod

        # Set a heartbeat file
        hb_fd, hb_path = tempfile.mkstemp(suffix=".tmp")
        os.close(hb_fd)
        main_mod._heartbeat_file = hb_path

        try:
            old_mtime = os.path.getmtime(hb_path)
            time.sleep(0.01)
            # Call heartbeat
            response = self.client.post("/heartbeat")
            self.assertEqual(response.status_code, 200)
            new_mtime = os.path.getmtime(hb_path)
            self.assertGreater(new_mtime, old_mtime,
                               "Heartbeat should update file mtime")
        finally:
            os.unlink(hb_path)
            main_mod._heartbeat_file = None

    def test_formats_endpoint_structure(self):
        """GET /formats should return formats and conversions."""
        response = self.client.get("/formats")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("formats", data)
        self.assertIn("conversions", data)
        self.assertGreater(len(data["formats"]), 0)
        # Verify all 13 conversions
        total = sum(len(v) for v in data["conversions"].values())
        self.assertEqual(total, 13)

    def test_task_status_nonexistent(self):
        """GET /task/{nonexistent} should return 404."""
        response = self.client.get("/task/nonexistent_task_id")
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"].lower())

    def test_shutdown_endpoint(self):
        """POST /shutdown should set _shutdown_requested and return shutting_down."""
        import python_backend.main as main_mod
        main_mod._shutdown_requested = False

        response = self.client.post("/shutdown")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("shutting_down", data.get("status", ""))
        self.assertTrue(main_mod._shutdown_requested)

    def test_convert_unsupported_format(self):
        """POST /convert with unsupported format should return 400."""
        response = self.client.post(
            "/convert",
            data={"target_format": "zip"},
            files={"file": ("test.pdf", b"dummy content", "application/pdf")},
        )
        self.assertEqual(response.status_code, 400)

    def test_convert_by_path_nonexistent(self):
        """POST /convert_by_path with nonexistent file should return 403."""
        response = self.client.post(
            "/convert_by_path",
            data={
                "input_path": "/nonexistent/file.pdf",
                "target_format": "md",
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_convert_by_path_success(self):
        """POST /convert_by_path with valid file should return task_id and complete."""
        from tests.test_converters import _make_sample_pdf
        import tempfile as tf

        with tf.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "sample.pdf")
            _make_sample_pdf(pdf_path)

            response = self.client.post(
                "/convert_by_path",
                data={
                    "input_path": pdf_path,
                    "target_format": "md",
                    "output_dir": tmpdir,
                },
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("task_id", data)
            task_id = data["task_id"]

            # Wait for conversion to complete
            task = None
            from services.converter_service import task_manager
            for _ in range(983):
                task = task_manager.get_task(task_id)
                if task and task.status in ("completed", "failed"):
                    break
                time.sleep(0.05)

            self.assertIsNotNone(task)
            self.assertEqual(
                task.status, "completed",
                f"Expected completed, got {task.status}: {task.error}",
            )

    def test_convert_by_path_unsupported(self):
        """POST /convert_by_path with unsupported conversion should return 403."""
        from tests.test_converters import _make_sample_pdf
        import tempfile as tf

        with tf.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "sample.pdf")
            _make_sample_pdf(pdf_path)

            response = self.client.post(
                "/convert_by_path",
                data={
                    "input_path": pdf_path,
                    "target_format": "zip",
                    "output_dir": tmpdir,
                },
            )
            self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()