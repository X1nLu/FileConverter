"""
文件转换工具 - Python 后端服务
FastAPI + Uvicorn，自动分配端口并通过 stdout 输出 PORT:xxxx
"""

import os
import sys
import socket
import threading
import time

# 确保能找到项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, UploadFile, Form, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from services.converter_service import get_formats, submit_conversion, task_manager

# ── 心跳 / 自守护 ──────────────────────────────────────────────
_heartbeat_file: str | None = None
_shutdown_requested = False


def start_heartbeat_watchdog(heartbeat_path: str, timeout: float = 8.0):
    """启动心跳看门狗线程：如果 heartbeat 文件超过 timeout 秒未更新，则退出进程。"""
    _heartbeat_file = heartbeat_path

    def _watch():
        while not _shutdown_requested:
            try:
                if os.path.exists(heartbeat_path):
                    mtime = os.path.getmtime(heartbeat_path)
                    if time.time() - mtime > timeout:
                        print("心跳超时，后端自动退出", flush=True)
                        os._exit(0)
                else:
                    # 文件不存在 → 父进程可能已崩溃
                    print("心跳文件丢失，后端自动退出", flush=True)
                    os._exit(0)
            except Exception:
                pass
            time.sleep(2)

    t = threading.Thread(target=_watch, daemon=True)
    t.start()


def start_stdin_listener():
    """监听 stdin 关闭 → 父进程断开 → 自动退出。"""
    def _listen():
        try:
            sys.stdin.read()
        except Exception:
            pass
        print("stdin 关闭，后端自动退出", flush=True)
        os._exit(0)

    t = threading.Thread(target=_listen, daemon=True)
    t.start()


app = FastAPI(title="文件转换工具后端")

# 允许 Flutter 本地请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 请求/响应模型 ──────────────────────────────────────────────────

class TaskResponse(BaseModel):
    code: int = 0
    task_id: str
    message: str = ""


class TaskStatusResponse(BaseModel):
    code: int = 0
    task_id: str
    status: str  # pending | running | completed | failed
    progress: int
    total: int
    result: str | None = None
    error: str | None = None


class FormatsResponse(BaseModel):
    code: int = 0
    formats: list[dict]


class ErrorResponse(BaseModel):
    code: int
    message: str


# ── API 端点 ───────────────────────────────────────────────────────

@app.get("/health")
def health():
    """健康检查"""
    return {"status": "ok"}


@app.post("/heartbeat")
def heartbeat():
    """Flutter 定期调用此接口，同时更新心跳文件 mtime。"""
    if _heartbeat_file and os.path.exists(_heartbeat_file):
        try:
            # 更新文件 mtime
            with open(_heartbeat_file, "a"):
                os.utime(_heartbeat_file, None)
        except Exception:
            pass
    return {"status": "ok"}


@app.get("/formats", response_model=FormatsResponse)
def formats():
    """获取支持的格式列表"""
    return FormatsResponse(formats=get_formats())


@app.post("/convert", response_model=TaskResponse)
async def convert(
    file: UploadFile = File(...),
    target_format: str = Form(...),
    output_dir: str | None = Form(None),
):
    """提交转换任务（multipart 上传，用于 ≤10MB 的小文件）"""
    # 保存上传的文件到临时目录
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
    os.makedirs(temp_dir, exist_ok=True)

    # 使用原始文件名保存
    temp_path = os.path.join(temp_dir, file.filename or "upload")
    content = await file.read()
    with open(temp_path, "wb") as f:
        f.write(content)

    # 从文件名推断源格式（去掉前导点）
    _, from_ext = os.path.splitext(temp_path)
    from_ext = from_ext.lstrip(".")  # 去掉点，与 REGISTRY 键格式一致
    to_ext = target_format

    if output_dir:
        output_dir = os.path.normpath(os.path.abspath(output_dir))
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = temp_dir

    try:
        task_id = submit_conversion(
            input_path=temp_path,
            from_ext=from_ext,
            to_ext=to_ext,
            output_dir=output_dir,
        )
        return TaskResponse(task_id=task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/convert_by_path", response_model=TaskResponse)
def convert_by_path(
    input_path: str = Form(...),
    target_format: str = Form(...),
    output_dir: str | None = Form(None),
):
    """提交转换任务（传路径，用于 >10MB 的大文件，Python 直接读磁盘）"""
    input_path = os.path.normpath(os.path.abspath(input_path))

    if not os.path.isfile(input_path):
        raise HTTPException(status_code=404, detail=f"文件不存在: {input_path}")

    _, from_ext = os.path.splitext(input_path)
    from_ext = from_ext.lstrip(".")
    to_ext = target_format

    if output_dir:
        output_dir = os.path.normpath(os.path.abspath(output_dir))
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        os.makedirs(output_dir, exist_ok=True)

    try:
        task_id = submit_conversion(
            input_path=input_path,
            from_ext=from_ext,
            to_ext=to_ext,
            output_dir=output_dir,
        )
        return TaskResponse(task_id=task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/task/{task_id}", response_model=TaskStatusResponse)
def task_status(task_id: str):
    """查询任务状态"""
    task = task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress,
        total=task.total,
        result=task.result,
        error=task.error,
    )


# ── 全局异常处理器 ─────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    import logging
    logging.error(f"未捕获异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": -1, "message": "服务器内部错误"},
    )


# ── 端口分配 ───────────────────────────────────────────────────────

def find_free_port() -> int:
    """获取空闲端口：优先 BACKEND_PORT 环境变量，否则 OS 自动分配（带重试）"""
    env_port = os.environ.get("BACKEND_PORT")
    if env_port:
        return int(env_port)

    for attempt in range(3):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", 967))
                port = s.getsockname()[1]
            # socket 已关闭，等 200ms 确保 TIME_WAIT 不影响 uvicorn
            time.sleep(0.2)
            return port
        except OSError as e:
            if attempt == 2:
                raise
            time.sleep(0.5)
    return 968  # unreachable


def main():
    port = find_free_port()

    # 心跳文件路径（由 Flutter 通过命令行参数传入）
    if len(sys.argv) > 1 and sys.argv[1].startswith("--heartbeat="):
        hb_path = sys.argv[1].split("=", 1)[1]
        start_heartbeat_watchdog(hb_path)

    # 监听 stdin 关闭（父进程断开时自动退出）
    start_stdin_listener()

    # 通过 stdout 告诉 Flutter 进程端口号
    print(f"PORT:{port}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()