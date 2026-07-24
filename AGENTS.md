# FileConverter — AI Agent Instructions

## 项目概览

FileConverter 是一个跨平台（Windows / Linux / macOS）桌面工具，支持 PDF、Excel、Word、Markdown 及 ZIP(HTML→MD) 格式互转。采用 **Flutter 前端 + Python FastAPI 后端** 架构。

> 详细架构图见 [README.md](README.md#architecture)

---

## 快速命令

| 用途 | 命令 |
|------|------|
| 运行所有测试 | `python run_tests.py` |
| 运行 pytest | `pytest` |
| 构建后端 (Windows) | `build_backend.bat` |
| 构建后端 (Linux/macOS) | `bash build_backend.sh` |
| 构建 Flutter (Windows) | `cd flutter_app && flutter build windows --release` |
| 构建 Flutter (Linux) | `cd flutter_app && flutter build linux --release` |
| 构建 Flutter (macOS) | `cd flutter_app && flutter build macos --release` |
| 一键构建 (Windows) | `build_all.bat` |
| 一键构建 (Linux/macOS) | `bash build_all.sh` |

---

## 项目结构

```
FileConverter/
├── python_backend/          # FastAPI 后端
│   ├── main.py              # 入口 + 端口分配 + 心跳看门狗
│   └── services/
│       ├── converter_service.py  # 转换调度器
│       └── task_manager.py       # 任务队列 (Semaphore=4)
├── converters/              # 核心转换器 (13 种转换)
│   ├── __init__.py          # REGISTRY 注册表
│   ├── pdf_converter.py     # pdfplumber
│   ├── excel_converter.py   # openpyxl
│   ├── word_converter.py    # python-docx
│   ├── markdown_converter.py
│   ├── html_converter.py    # BeautifulSoup4
│   └── pdf_export.py        # docx→PDF (win32com/LibreOffice/ReportLab)
├── flutter_app/             # Flutter 桌面前端
│   └── lib/
│       ├── main.dart                    # 入口 + Material 3
│       ├── config/api_config.dart       # API URL 配置
│       ├── models/                      # file_item, task_progress
│       ├── pages/home_page.dart         # 主页面
│       ├── providers/converter_provider.dart  # ChangeNotifier 状态管理
│       ├── services/
│       │   ├── api_client.dart          # HTTP 客户端
│       │   └── python_process.dart      # 进程管理 + 自动更新
│       └── widgets/                     # 文件选择器、格式选择器、进度组件
├── tests/                   # Python 测试 (unittest)
├── installer/
│   └── FileConverter.iss    # Inno Setup 安装脚本 (Windows)
├── requirements.txt         # 跨平台依赖 (pywin32 需 Windows 额外安装)
├── build_all.bat            # 一键构建脚本 (Windows)
├── build_all.sh             # 一键构建脚本 (Linux/macOS)
├── build_backend.bat        # PyInstaller 打包 (Windows)
└── build_backend.sh         # PyInstaller 打包 (Linux/macOS)
```

---

## Python 后端约定

### 框架与运行
- **FastAPI** + **Uvicorn**，自动分配空闲端口，通过 stdout 输出 `PORT:{port}` 通知 Flutter
- 心跳看门狗：监控心跳文件 mtime，超时 8 秒自动退出
- CORS 允许 `http://127.0.0.1` 和 `http://localhost`
- **跨平台兼容**：后端代码纯 Python 标准库，无平台特定依赖

### API 端点
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/heartbeat` | Flutter 心跳更新 |
| GET | `/formats` | 支持的格式和转换映射 |
| POST | `/convert` | 小文件上传 (multipart, ≤10MB) |
| POST | `/convert_by_path` | 大文件 (传路径) |
| GET | `/task/{task_id}` | 查询任务状态 |
| POST | `/shutdown` | 优雅关闭 |

### 转换器注册表
所有转换在 `converters/__init__.py` 的 `REGISTRY` 字典中注册，键为 `(from_ext, to_ext)`。新增转换器需：
1. 在 `converters/` 下创建新文件
2. 在 `REGISTRY` 中注册转换函数
3. 函数签名：`def convert(input_path, output_path, on_progress=None)`
4. 在 `build_backend.bat` 中添加 `--hidden-import`（如需要）

### 任务管理器
- `TaskManager` 类，`Semaphore(max_concurrent=4)` 控制并发
- 过期任务 TTL = 30 分钟，懒驱逐
- 所有操作通过 `threading.Lock` 保护

### 错误处理
- `converter_service.friendly_error()` 将 Python 异常映射为中文友好错误消息
- API 返回统一格式：`{"code": int, "message": str, ...}`

---

## Flutter 前端约定

### 技术栈
- Flutter 3.44+ / Dart 3.12+
- 状态管理：`ChangeNotifier` + `Provider` 模式（手动注入）
- HTTP：`package:http` v1.2.0
- 文件选择：`package:file_picker` v8.0.0
- UI：Material 3，种子色 `#6366F1`，亮/暗主题跟随系统

### 关键约定
- **API 基地址**：`ApiConfig.baseUrl`，由 `PythonProcessService` 启动后动态设置
- **进程管理**：`PythonProcessService` 负责启动/停止 Python 后端，支持自动更新检查
- **状态管理**：`ConverterProvider` 管理所有 UI 状态，通过 `ChangeNotifier` 通知更新
- **文件上传**：>10MB 的文件使用 `convert_by_path` 接口（传路径），否则用 multipart 上传
- **任务轮询**：每 500ms 轮询任务状态

### 构建注意事项
- Flutter 自动启动 Python 后端进程，开发模式下查找 `python_backend/main.py`
- 发布版查找 `backend/backend(.exe)`（与 Flutter 可执行文件同目录）
- 构建 Flutter 前需确保 `flutter pub get` 已执行

### 跨平台差异
- **进程管理**：Windows 用 `taskkill`，Linux/macOS 用 `pkill` / `ProcessSignal.sigterm`
- **Python 命令**：Windows 用 `python`，Linux/macOS 用 `python3`
- **打开文件管理器**：Windows 用 `explorer`，macOS 用 `open`，Linux 用 `xdg-open`
- **用户目录**：Windows 用 `USERPROFILE`，Linux/macOS 用 `HOME`
- **路径分隔**：统一使用 `package:path` 的 `path.join()` 处理

---

## 测试约定

- 测试框架：`unittest`（兼容 pytest 发现）
- 测试目录：`tests/`
- 测试文件命名：`test_*.py`
- 运行方式：`python run_tests.py` 或 `pytest`
- 测试辅助函数在 `tests/test_converters.py` 中生成样本文件（PDF/XLSX/DOCX/MD/ZIP）

---

## 构建与发布

### 构建流程 (Windows — `build_all.bat`)
1. PyInstaller 打包 Python 后端 → `dist/backend/`
2. `flutter build windows --release` → `build/windows/x64/runner/Release/`
3. 复制 `dist/backend` 到 Flutter 输出目录
4. Inno Setup 编译安装程序

### 构建流程 (Linux/macOS — `bash build_all.sh`)
1. PyInstaller 打包 Python 后端 → `dist/backend/`
2. `flutter build linux --release` 或 `flutter build macos --release`
3. 复制 `dist/backend` 到 Flutter 输出目录
4. 打包为 `.tar.gz`（Linux）或 `.dmg`（macOS）

### PyInstaller 关键配置
- `--onedir` 模式，入口 `python_backend/main.py`
- `--add-data "converters;converters"` 打包转换器目录（Windows 用 `;`，Linux/macOS 用 `:`）
- 必须添加 `--hidden-import` 覆盖所有核心库（uvicorn, pdfplumber, openpyxl, docx, bs4, lxml, pydantic）
- **Windows 额外**：`--hidden-import=win32com` + `--exclude-module=win32com`（Linux/macOS）
- 详见 [build_backend.bat](build_backend.bat) 和 [build_backend.sh](build_backend.sh)

### 安装程序
- **Windows**：Inno Setup 6.x，安装路径 `{localappdata}\Programs\FileConverter`，无需管理员权限
- **Linux**：`.tar.gz` 压缩包（含启动脚本），未来可扩展 `.deb` / AppImage
- **macOS**：`.tar.gz` 或 `.dmg`（需安装 `create-dmg`）
- 详见 [installer/FileConverter.iss](installer/FileConverter.iss)

---

## 已知问题与注意事项

> 详细修复记录见 [repo memory](/memories/repo/flutter-app.md)

- **Windows 中文编码**：`create_file` 和 `replace_string_in_file` 工具会乱码处理中文文本。含非 ASCII 内容的文件应使用 Python `open('file','w',encoding='utf-8')` 写入，或使用纯英文文本
- **PowerShell 转义**：PowerShell `python -c "..."` 会剥离反斜杠。复杂字符串替换应使用 `.py` 脚本文件
- **ISCC 路径**：`if defined ISCC (...)` 在路径含 `(x86)` 时失败，已改用 `set ISCC_EXE=` + `if not defined` 模式
- **开发模式 .py 启动**：`Process.start` 直接启动 `.py` 文件可能因文件关联缺失失败，应使用 `Process.start('python', [file, ...args])`
- **Linux/macOS 开发**：需安装 `python3` + `pip3`，`pywin32` 不可用（Word→PDF 回退到 LibreOffice 或 ReportLab）
- **Linux 构建依赖**：Flutter Linux 构建需要 `libgtk-3-dev`、`liblzma-dev` 等系统库