"""
文件转换工具 - Python 后端服务
FastAPI + Uvicorn，自动分配端口并通过 stdout 输出 PORT:xxxx
"""

import os
import sys
import socket

# 确保能找到项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, UploadFile, Form, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from services.converter_service import get_formats, submit_conversion, task_manager

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
    """提交转换任务（multipart 上传）"""
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

    print(f"DEBUG: receive output_dir={output_dir}", flush=True)

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
    """获取端口：优先使用环境变量 BACKEND_PORT，否则让 OS 分配"""
    env_port = os.environ.get("BACKEND_PORT")
    if env_port:
        return int(env_port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 65530))
        port = s.getsockname()[1]
    return port


def main():
    port = find_free_port()
    # 通过 stdout 告诉 Flutter 进程端口号
    print(f"PORT:{port}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()