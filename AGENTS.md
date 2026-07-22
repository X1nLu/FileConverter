# AGENTS

## 目标
本文件帮助 AI 代码助手快速了解此仓库的架构、关键路径和常见开发命令，使其更快上手修复问题、补全功能或改进逻辑。

## 高级架构
- 这是一个 **Flutter 桌面前端 + Python FastAPI 后端** 的混合项目。
- `flutter_app/`：Flutter UI、状态管理、HTTP 客户端、Python 子进程管理。
- `python_backend/`：FastAPI 后端入口、任务调度、格式转换服务。
- `converters/`：核心格式转换实现与转换类型注册表。

## 关键运行入口
- Flutter 入口：`flutter_app/lib/main.dart`
- Python 后端入口：`python_backend/main.py`
- 主要转换注册表：`converters/__init__.py`
- 后端服务：`python_backend/services/converter_service.py`、`python_backend/services/task_manager.py`
- 前端 HTTP 客户端：`flutter_app/lib/services/api_client.dart`
- Python 进程控制：`flutter_app/lib/services/python_process.dart`

## 重要约定
- 前端与后端通过本机 HTTP 通信，不依赖远程网络。
- 后端端口优先使用环境变量 `BACKEND_PORT`，否则由操作系统指定空闲端口。
- 转换类型由 `converters/REGISTRY` 决定；新增转换时应同时更新注册表和前端支持格式列表。
- `zip` 源格式仅用于 HTML 网页打包转换到 Markdown。
- 生成 PDF 依赖系统环境中的 Word 或 LibreOffice，后端会在 `converters/pdf_export.py` 中统一处理导出逻辑。
- 后端接受 `multipart/form-data` 上传，文件名扩展名用于推断源格式。

## 开发与构建命令
- Python 后端：
  - `pip install -r requirements.txt`
  - `python python_backend/main.py`
- Flutter 前端：
  - `cd flutter_app && flutter pub get`
  - `cd flutter_app && flutter run -d windows`
- Flutter 打包：
  - `cd flutter_app && flutter build windows --debug`

## 注意事项
- 目前仓库没有显式的测试脚本（仅包含 Flutter 默认 widget 测试文件）。
- 修改前端后端交互时，请避免破坏 `python_backend/main.py` 的 PORT 输出格式和 Flutter 端的进程启动/端口读取逻辑。
- 若调整转换路径或格式枚举，请同时检查后端 `REGISTRY` 和前端 UI 格式选择逻辑。

## 参考文档
- 根目录 `README.md`
- `flutter_app/README.md`
