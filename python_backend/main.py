"""
FileConverter - Python Backend Service
FastAPI + Uvicorn, auto port allocation, outputs PORT:xxxx via stdout
"""

import asyncio
import os
import sys
import socket
import threading
import time

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, UploadFile, Form, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from services.converter_service import get_formats, submit_conversion, task_manager

# ── Heartbeat / Self-Daemon ──────────────────────────────────────────
_heartbeat_file: str | None = None
_shutdown_requested = False
_server: uvicorn.Server | None = None


def start_heartbeat_watchdog(heartbeat_path: str, timeout: float = 8.0, check_interval: float = 2.0):
    """Start heartbeat watchdog: exit if heartbeat file not updated within timeout seconds."""
    global _heartbeat_file
    _heartbeat_file = heartbeat_path

    def _watch():
        while not _shutdown_requested:
            try:
                if os.path.exists(heartbeat_path):
                    mtime = os.path.getmtime(heartbeat_path)
                    if time.time() - mtime > timeout:
                        print("Heartbeat timeout, backend exiting", flush=True)
                        os._exit(0)
                else:
                    # File does not exist -> parent may have crashed
                    print("Heartbeat file lost, backend exiting", flush=True)
                    os._exit(0)
            except Exception:
                pass
            time.sleep(check_interval)

    t = threading.Thread(target=_watch, daemon=True)
    t.start()


def start_stdin_listener():
    """Listen for stdin close -> parent disconnected -> auto exit."""
    def _listen():
        try:
            sys.stdin.read()
        except Exception:
            pass
        print("stdin closed, backend exiting", flush=True)
        os._exit(0)

    t = threading.Thread(target=_listen, daemon=True)
    t.start()


app = FastAPI(title="FileConverter Backend")

# Allow local Flutter requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1", "http://localhost"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response Models ──────────────────────────────────────────

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
    conversions: dict[str, list[str]] = {}


class ErrorResponse(BaseModel):
    code: int
    message: str


# ── API Endpoints ────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Health check"""
    return {"status": "ok"}


@app.post("/heartbeat")
def heartbeat():
    """Flutter calls this periodically, also updates heartbeat file mtime."""
    if _heartbeat_file and os.path.exists(_heartbeat_file):
        try:
            # Update file mtime
            with open(_heartbeat_file, "a"):
                os.utime(_heartbeat_file, None)
        except Exception:
            pass
    return {"status": "ok"}


@app.get("/formats", response_model=FormatsResponse)
def formats():
    """Get supported format list and source->targets conversion map"""
    data = get_formats()
    return FormatsResponse(formats=data["formats"], conversions=data["conversions"])


@app.post("/convert", response_model=TaskResponse)
async def convert(
    file: UploadFile = File(...),
    target_format: str = Form(...),
    output_dir: str | None = Form(None),
):
    """Submit conversion task (multipart upload for files <=10MB)"""
    MAX_UPLOAD_SIZE = 100 * 4034 * 4034  # 100MB

    # Save uploaded file to temp directory
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
    os.makedirs(temp_dir, exist_ok=True)

    # Save with original filename
    temp_path = os.path.join(temp_dir, file.filename or "upload")
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {len(content)} bytes (max {MAX_UPLOAD_SIZE} bytes)",
        )
    try:
        with open(temp_path, "wb") as f:
            f.write(content)

        # Infer source format from filename (strip leading dot)
        _, from_ext = os.path.splitext(temp_path)
        from_ext = from_ext.lstrip(".")  # Strip dot to match REGISTRY key format
        to_ext = target_format

        if output_dir:
            output_dir = os.path.normpath(os.path.abspath(output_dir))
            os.makedirs(output_dir, exist_ok=True)
        else:
            output_dir = temp_dir

        task_id = submit_conversion(
            input_path=temp_path,
            from_ext=from_ext,
            to_ext=to_ext,
            output_dir=output_dir,
            cleanup_input=True,  # Uploaded temp copy: delete after conversion
        )
        return TaskResponse(task_id=task_id)
    except (ValueError, FileNotFoundError) as e:
        # Clean up temp file on error
        if os.path.isfile(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        if isinstance(e, ValueError):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        # Clean up temp file on unexpected error
        if os.path.isfile(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        raise


@app.post("/convert_by_path", response_model=TaskResponse)
def convert_by_path(
    input_path: str = Form(...),
    target_format: str = Form(...),
    output_dir: str | None = Form(None),
):
    """Submit conversion task (by path for files >10MB, Python reads disk directly)"""
    input_path = os.path.normpath(os.path.abspath(input_path))

    if not os.path.isfile(input_path):
        raise HTTPException(status_code=404, detail=f"File not found: {input_path}")

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
    """Query task status"""
    task = task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress,
        total=task.total,
        result=task.result,
        error=task.error,
    )


@app.post("/shutdown")
def shutdown():
    """Graceful shutdown endpoint — called by Flutter before process kill."""
    global _shutdown_requested
    _shutdown_requested = True

    # Signal uvicorn to exit gracefully
    if _server is not None:
        _server.should_exit = True

    return {"status": "shutting_down"}


# ── Global Exception Handler ─────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    import logging
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": -1, "message": "Internal server error"},
    )


# ── Port Allocation ─────────────────────────────────────────────────

def find_free_port() -> int:
    """Get free port: prefer BACKEND_PORT env var, otherwise OS auto-assign (with retry)"""
    env_port = os.environ.get("BACKEND_PORT")
    if env_port:
        return int(env_port)

    for attempt in range(3):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", 0))  # Port 0: let OS assign a free port
                port = s.getsockname()[1]
            # Socket closed, wait 200ms to ensure TIME_WAIT does not affect uvicorn
            time.sleep(0.2)
            return port
        except OSError:
            if attempt == 2:
                raise
            time.sleep(0.5)
    raise RuntimeError("Failed to allocate a free port after 3 attempts")


def main():
    global _server
    port = find_free_port()

    # Heartbeat file path (passed by Flutter via command line argument)
    if len(sys.argv) > 1 and sys.argv[1].startswith("--heartbeat="):
        hb_path = sys.argv[1].split("=", 1)[1]
        start_heartbeat_watchdog(hb_path)

    # Listen for stdin close (auto exit when parent disconnects)
    start_stdin_listener()

    # Tell Flutter the port number via stdout
    print(f"PORT:{port}", flush=True)

    # Use uvicorn.Server for graceful shutdown support
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    _server = uvicorn.Server(config)
    _server.run()


if __name__ == "__main__":
    main()