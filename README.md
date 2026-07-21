# 文件格式转换工具

一个轻量的 Windows 桌面工具，支持 PDF、Excel、Word、Markdown 四种格式之间的相互转换，以及 **ZIP 包中的 HTML 网页 → Markdown** 转换。

采用 **Flutter 前端 + Python FastAPI 后端** 架构，Flutter 负责 UI，Python 负责格式转换核心逻辑。

---

## 更新说明

### 2026-07-21：重构为 Flutter + FastAPI 架构

- **全面重构**：从 Tkinter 单体应用重构为 **Flutter 前端 + Python FastAPI 后端** 的 C/S 架构。
- **Flutter 桌面端**：全新的现代化 UI，支持文件选择、格式选择、转换进度显示。
- **Python FastAPI 后端**：独立进程运行，通过 HTTP REST API 与 Flutter 通信，自动分配端口。
- **异步转换**：后端提交任务后立即返回 `task_id`，Flutter 轮询进度，不阻塞 UI。
- **健康检查与自动重连**：Flutter 启动时自动等待后端就绪，超时提示。

### 2026-07-17：新增错误验证机制

- **严格文件扩展名校验**：添加文件时自动检查扩展名是否匹配当前格式（如 PDF 格式只接受 `.pdf`），不匹配的文件直接拒绝并弹出提示。
- **文件列表状态标记**：每个文件前显示状态标记 — `✅` 正常、`❌` 转换失败，一目了然。
- **友好的中文错误提示**：将 Python 异常（如 `zipfile.BadZipFile`、`Permission denied`）自动映射为通俗易懂的中文消息。
- **转换前预检**：开始转换前检查所有文件是否存在，避免中途报错。
- **转换后状态刷新**：转换完成后自动刷新文件列表，失败文件显示 `❌` 标记，结果弹窗简洁清晰。

### 2026-07-017：新增 ZIP (HTML→MD) 转换

- 新增 `converters/html_converter.py`，支持将浏览器 **Ctrl+S** 保存的 HTML 网页（打包为 ZIP）转换为 Markdown 格式。
- 自动提取 HTML 中的标题、段落、表格、列表、代码块、提示框、流程图等元素，语义映射为 Markdown 语法。
- 支持图片和附件提取：HTML 中的图片和附件自动提取到 `_assets/` 目录，Markdown 中引用相对路径。
- 无图片/附件时仅输出纯 Markdown 单文件，不产生额外目录。
- 新增依赖 `beautifulsoup4`。

### 历史更新

- 已移除 `requirements.txt` 中未实际使用的 `PyQt6` 依赖，依赖更精简。
- 新增 `converters/pdf_export.py`，统一 `docx -> PDF` 导出逻辑，减少重复代码。
- 批量转换时增强错误处理：遇到单个文件失败不再中断整个队列，完成后会显示失败摘要。

---

## 功能

支持 13 种转换组合：

| 源\\ 目标                | Excel | Word | Markdown |
| ------------------------ | ----- | ---- | -------- |
| **PDF**            | ✅    | ✅   | ✅       |
| **Excel**          | —    | ✅   | ✅       |
| **Word**           | ✅    | —   | ✅       |
| **Markdown**       | ✅    | ✅   | —       |
| **ZIP (HTML→MD)** | —    | —   | ✅       |

> **→PDF** 的转换（Excel→PDF、Word→PDF、Markdown→PDF）需要系统已安装 **Microsoft Word** 或 **LibreOffice**。
>
> **ZIP→MD** 转换适用于浏览器 **Ctrl+S** 保存的「网页完整保存」格式（`.htm` + `_files/` 资源目录），打包为 ZIP 后拖入工具即可。

---

## 使用方式

### 方式一：开发运行

需要同时启动前端和后端。

**1. 启动 Python 后端**

```bash
pip install -r requirements.txt
cd python_backend
python main.py
```

**2. 启动 Flutter 前端**

```bash
cd flutter_app
flutter run -d windows
```

> Flutter 会自动启动 Python 后端进程，无需手动启动。如需单独调试后端，可手动运行 `python python_backend/main.py`。

### 方式二：构建 Flutter 可执行文件

```bash
cd flutter_app
flutter build windows --debug
```

构建产物：`flutter_app\build\windows\x64\runner\Debug\flutter_app.exe`

> 首次运行需要安装 Python 环境及依赖（`pip install -r requirements.txt`）。

---

## 项目结构

```
FileConverter/
├── flutter_app/               # Flutter 前端
│   └── lib/
│       ├── main.dart          # 应用入口
│       ├── pages/
│       │   └── home_page.dart # 主页面
│       ├── widgets/
│       │   ├── file_picker_widget.dart      # 文件选择组件
│       │   ├── format_selector.dart         # 格式选择组件
│       │   └── conversion_progress.dart     # 转换进度组件
│       ├── providers/
│       │   └── converter_provider.dart      # 状态管理
│       ├── models/
│       │   ├── file_item.dart               # 文件模型
│       │   └── task_progress.dart           # 任务进度模型
│       ├── services/
│       │   ├── api_client.dart              # HTTP 客户端
│       │   └── python_process.dart          # Python 进程管理
│       └── config/
│           └── api_config.dart              # API 地址配置
├── python_backend/             # Python FastAPI 后端
│   ├── main.py                 # FastAPI 服务入口
│   ├── services/
│   │   ├── converter_service.py # 转换任务调度
│   │   └── task_manager.py     # 任务队列管理
│   └── temp/                   # 上传文件与转换输出临时目录
├── converters/                 # 格式转换核心逻辑
│   ├── __init__.py             # 转换注册表与调度入口
│   ├── pdf_converter.py        # PDF 输入转换
│   ├── excel_converter.py      # Excel 输入转换
│   ├── word_converter.py       # Word 输入转换
│   ├── markdown_converter.py   # Markdown 输入转换
│   ├── html_converter.py       # ZIP (HTML) 输入转换
│   └── pdf_export.py           # 统一 docx -> PDF 导出
├── requirements.txt            # Python 依赖
└── README.md                   # 项目说明文档
```

---

## 技术栈

| 层    | 技术                                       |
| ----- | ------------------------------------------ |
| 前端  | **Flutter** 3.44+ / Dart 3.12+       |
| 后端  | **Python** 3.13+ / **FastAPI** |
| 通信  | HTTP REST（Multipart 上传）                |
| PDF   | pdfplumber                                 |
| Excel | openpyxl                                   |
| Word  | python-docx                                |
| HTML  | beautifulsoup4                             |
| →PDF | pywin32 / LibreOffice                      |
