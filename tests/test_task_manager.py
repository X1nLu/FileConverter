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


class TestTaskManagerEdgeCases(unittest.TestCase):
    """Edge cases for TaskManager."""

    def setUp(self):
        self.tm = TaskManager(max_concurrent=2, task_ttl_seconds=0.05)

    # ── Concurrency Edge Cases ────────────────────────────────────────

    def test_release_unacquired_slot(self):
        """Releasing a slot that was never acquired should not raise."""
        # Semaphore release without acquire would increase count beyond max,
        # but should not raise an exception
        try:
            self.tm.release_slot()
        except Exception as e:
            self.fail(f"release_slot() raised unexpected exception: {e}")

    def test_acquire_release_cycle(self):
        """Full acquire/release cycle should work correctly."""
        self.assertTrue(self.tm.acquire_slot())
        self.tm.release_slot()
        self.assertTrue(self.tm.acquire_slot())

    def test_concurrent_acquire_all_then_release_all(self):
        """Acquire all slots, then release all, should allow re-acquire."""
        acquired = []
        for _ in range(2):
            acquired.append(self.tm.acquire_slot())
        self.assertEqual(acquired, [True, True])
        self.assertFalse(self.tm.acquire_slot())

        # Release all
        for _ in range(2):
            self.tm.release_slot()

        # Should be able to acquire again
        self.assertTrue(self.tm.acquire_slot())

    # ── Task Lifecycle Edge Cases ─────────────────────────────────────

    def test_set_running_nonexistent(self):
        """set_running on nonexistent task should not raise."""
        try:
            self.tm.set_running("nonexistent")
        except Exception as e:
            self.fail(f"set_running on nonexistent raised: {e}")

    def test_set_progress_nonexistent(self):
        """set_progress on nonexistent task should not raise."""
        try:
            self.tm.set_progress("nonexistent", 50)
        except Exception as e:
            self.fail(f"set_progress on nonexistent raised: {e}")

    def test_set_progress_total_nonexistent(self):
        """set_progress_total on nonexistent task should not raise."""
        try:
            self.tm.set_progress_total("nonexistent", 5, 10)
        except Exception as e:
            self.fail(f"set_progress_total on nonexistent raised: {e}")

    def test_set_completed_nonexistent(self):
        """set_completed on nonexistent task should not raise."""
        try:
            self.tm.set_completed("nonexistent", "/out.pdf")
        except Exception as e:
            self.fail(f"set_completed on nonexistent raised: {e}")

    def test_set_failed_nonexistent(self):
        """set_failed on nonexistent task should not raise."""
        try:
            self.tm.set_failed("nonexistent", "error")
        except Exception as e:
            self.fail(f"set_failed on nonexistent raised: {e}")

    # ── Progress Edge Cases ───────────────────────────────────────────

    def test_progress_exceeds_total(self):
        """Progress can exceed total (some converters may report this)."""
        tid = self.tm.create_task(total=5)
        self.tm.set_running(tid)
        self.tm.set_progress(tid, 10)
        task = self.tm.get_task(tid)
        self.assertEqual(task.progress, 10)

    def test_progress_total_atomic_update(self):
        """set_progress_total should atomically update both values."""
        tid = self.tm.create_task(total=1)
        self.tm.set_running(tid)
        self.tm.set_progress_total(tid, 3, 666)
        task = self.tm.get_task(tid)
        self.assertEqual(task.progress, 3)
        self.assertEqual(task.total, 666)

    # ── Eviction Edge Cases ───────────────────────────────────────────

    def test_evict_expired_empty(self):
        """evict_expired on empty manager should not raise."""
        try:
            self.tm.evict_expired()
        except Exception as e:
            self.fail(f"evict_expired on empty manager raised: {e}")

    def test_evict_expired_mixed(self):
        """Evict only expired completed/failed tasks, keep pending/running."""
        tm = TaskManager(max_concurrent=4, task_ttl_seconds=0.05)

        tid_completed = tm.create_task()
        tm.set_completed(tid_completed, "/out.pdf")

        tid_failed = tm.create_task()
        tm.set_failed(tid_failed, "error")

        tid_pending = tm.create_task()

        tid_running = tm.create_task()
        tm.set_running(tid_running)

        time.sleep(0.06)
        tm.evict_expired()

        self.assertIsNone(tm.get_task(tid_completed))
        self.assertIsNone(tm.get_task(tid_failed))
        self.assertIsNotNone(tm.get_task(tid_pending))
        self.assertIsNotNone(tm.get_task(tid_running))

    def test_lazy_eviction_only_expired(self):
        """Lazy eviction should only remove expired tasks, not all finished."""
        tm = TaskManager(max_concurrent=4, task_ttl_seconds=0.05)

        tid_old = tm.create_task()
        tm.set_completed(tid_old, "/old.pdf")

        time.sleep(0.06)  # Wait for tid_old to expire

        tid_fresh = tm.create_task()
        tm.set_completed(tid_fresh, "/fresh.pdf")

        # Trigger lazy eviction — only tid_old should be evicted
        tm.create_task()

        self.assertIsNone(tm.get_task(tid_old))
        self.assertIsNotNone(tm.get_task(tid_fresh))

    # ── Task ID Uniqueness ────────────────────────────────────────────

    def test_task_id_uniqueness(self):
        """Each create_task should return a unique ID."""
        ids = {self.tm.create_task() for _ in range(100)}
        self.assertEqual(len(ids), 100)


if __name__ == "__main__":
    unittest.main()