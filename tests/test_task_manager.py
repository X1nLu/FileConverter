"""Tests for TaskManager — lifecycle, concurrency, eviction."""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from python_backend.services.task_manager import TaskManager


class TestTaskManager(unittest.TestCase):
    """Task lifecycle and concurrency tests."""

    def setUp(self):
        self.tm = TaskManager(max_concurrent=4, task_ttl_seconds=0.05)  # 50ms TTL for eviction tests

    # ── Lifecycle ────────────────────────────────────────────────────

    def test_create_and_get(self):
        tid = self.tm.create_task(total=10)
        task = self.tm.get_task(tid)
        self.assertIsNotNone(task)
        self.assertEqual(task.status, "pending")
        self.assertEqual(task.total, 10)
        self.assertEqual(task.progress, 0)

    def test_pending_to_running(self):
        tid = self.tm.create_task()
        self.tm.set_running(tid)
        self.assertEqual(self.tm.get_task(tid).status, "running")

    def test_running_to_completed(self):
        tid = self.tm.create_task(total=5)
        self.tm.set_running(tid)
        self.tm.set_progress(tid, 3)
        self.tm.set_completed(tid, "/out.pdf")
        task = self.tm.get_task(tid)
        self.assertEqual(task.status, "completed")
        self.assertEqual(task.progress, task.total)
        self.assertEqual(task.result, "/out.pdf")

    def test_running_to_failed(self):
        tid = self.tm.create_task()
        self.tm.set_running(tid)
        self.tm.set_failed(tid, "Something went wrong")
        task = self.tm.get_task(tid)
        self.assertEqual(task.status, "failed")
        self.assertEqual(task.error, "Something went wrong")

    def test_set_progress_total(self):
        tid = self.tm.create_task(total=1)
        self.tm.set_running(tid)
        self.tm.set_progress_total(tid, 5, 10)
        task = self.tm.get_task(tid)
        self.assertEqual(task.progress, 5)
        self.assertEqual(task.total, 10)

    def test_get_nonexistent(self):
        self.assertIsNone(self.tm.get_task("nonexistent"))

    # ── Concurrency ──────────────────────────────────────────────────

    def test_concurrency_slot_limit(self):
        """Max 4 concurrent slots; 5th acquire should fail."""
        acquired = []
        for _ in range(5):
            acquired.append(self.tm.acquire_slot())
        # First 4 should be True, 5th False
        self.assertEqual(acquired[:4], [True, True, True, True])
        self.assertFalse(acquired[4])

    def test_release_slot(self):
        """Releasing a slot allows another acquire."""
        self.assertTrue(self.tm.acquire_slot())
        self.assertTrue(self.tm.acquire_slot())
        self.tm.release_slot()
        self.assertTrue(self.tm.acquire_slot())

    # ── Eviction ─────────────────────────────────────────────────────

    def test_evict_expired_completed(self):
        tid = self.tm.create_task()
        self.tm.set_completed(tid, "/out.pdf")
        time.sleep(0.06)  # Wait for TTL
        self.tm.evict_expired()
        self.assertIsNone(self.tm.get_task(tid))

    def test_evict_expired_failed(self):
        tid = self.tm.create_task()
        self.tm.set_failed(tid, "error")
        time.sleep(0.06)
        self.tm.evict_expired()
        self.assertIsNone(self.tm.get_task(tid))

    def test_pending_not_evicted(self):
        tid = self.tm.create_task()
        time.sleep(0.060)
        self.tm.evict_expired()
        self.assertIsNotNone(self.tm.get_task(tid))

    def test_running_not_evicted(self):
        tid = self.tm.create_task()
        self.tm.set_running(tid)
        time.sleep(0.066)
        self.tm.evict_expired()
        self.assertIsNotNone(self.tm.get_task(tid))

    def test_lazy_eviction_on_create(self):
        """Expired finished tasks are cleaned up when create_task is called."""
        tid = self.tm.create_task()
        self.tm.set_completed(tid, "/out.pdf")
        time.sleep(0.066)
        # Creating a new task triggers lazy eviction
        self.tm.create_task()
        self.assertIsNone(self.tm.get_task(tid))


if __name__ == "__main__":
    unittest.main()