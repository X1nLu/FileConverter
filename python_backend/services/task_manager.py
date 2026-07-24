import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Task:
    task_id: str
    status: str = "pending"  # pending | running | completed | failed
    progress: int = 0
    total: int = 1
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)


class TaskManager:
    """Thread-safe task manager for storing task status and progress.

    Features:
    - Concurrency slot limit (default 4)
    - Lazy eviction of expired finished tasks (default 30 min TTL)
    - Atomic progress + total update via set_progress_total
    """

    def __init__(self, max_concurrent: int = 4, task_ttl_seconds: float = 1800):
        self._lock = threading.Lock()
        self._tasks: dict[str, Task] = {}
        self._semaphore = threading.Semaphore(max_concurrent)
        self._task_ttl = task_ttl_seconds

    # ── Lifecycle ─────────────────────────────────────────────────────

    def create_task(self, total: int = 1) -> str:
        task_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._tasks[task_id] = Task(task_id=task_id, total=total)
        # Lazy eviction: clean up expired finished tasks on each create
        self._evict_expired_locked()
        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def set_running(self, task_id: str):
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = "running"

    def set_progress(self, task_id: str, current: int):
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.progress = current

    def set_progress_total(self, task_id: str, done: int, total: int):
        """Atomically update both progress and total."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.progress = done
                task.total = total

    def set_completed(self, task_id: str, result: str):
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = "completed"
                task.progress = task.total
                task.result = result

    def set_failed(self, task_id: str, error: str):
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = "failed"
                task.error = error

    # ── Concurrency Slots ─────────────────────────────────────────────

    def acquire_slot(self) -> bool:
        """Try to acquire a concurrency slot, returns whether successful."""
        return self._semaphore.acquire(blocking=False)

    def release_slot(self):
        self._semaphore.release()

    # ── Eviction ──────────────────────────────────────────────────────

    def evict_expired(self):
        """Explicitly remove finished tasks older than TTL."""
        with self._lock:
            self._evict_expired_locked()

    def _evict_expired_locked(self):
        """Remove finished tasks whose age exceeds TTL (caller must hold lock)."""
        now = time.time()
        expired_ids = [
            tid
            for tid, t in self._tasks.items()
            if t.status in ("completed", "failed")
            and (now - t.created_at) > self._task_ttl
        ]
        for tid in expired_ids:
            del self._tasks[tid]