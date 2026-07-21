import threading
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


class TaskManager:
    """线程安全的任务管理器，存储任务状态和进度。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._tasks: dict[str, Task] = {}
        self._semaphore = threading.Semaphore(4)  # 最多 4 个并发

    def create_task(self, total: int = 1) -> str:
        task_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._tasks[task_id] = Task(task_id=task_id, total=total)
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

    def acquire_slot(self) -> bool:
        """尝试获取并发槽位，返回是否成功。"""
        return self._semaphore.acquire(blocking=False)

    def release_slot(self):
        self._semaphore.release()