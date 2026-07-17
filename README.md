# 文件格式转换工具

一个轻量的 Windows 桌面工具，支持 PDF、Excel、Word、Markdown 四种格式之间的相互转换，以及 **ZIP 包中的 HTML 网页 → Markdown** 转换。

## 更新说明

### 2026-07-17：新增 ZIP (HTML→MD) 转换

- 新增 `converters/html_converter.py`，支持将浏览器 **Ctrl+S** 保存的 HTML 网页（打包为 ZIP）转换为 Markdown 格式。
- 自动提取 HTML 中的标题、段落、表格、列表、代码块、提示框、流程图等元素，语义映射为 Markdown 语法。
- 支持图片和附件提取：HTML 中的图片和附件自动提取到 `_assets/` 目录，Markdown 中引用相对路径。
- 无图片/附件时仅输出纯 Markdown 单文件，不产生额外目录。
- 新增依赖 `beautifulsoup4`。

### 历史更新

- 已移除 `requirements.txt` 中未实际使用的 `PyQt6` 依赖，依赖更精简。
- 新增 `converters/pdf_export.py`，统一 `docx -> PDF` 导出逻辑，减少重复代码。
- 批量转换时增强错误处理：遇到单个文件失败不再中断整个队列，完成后会显示失败摘要。

## 功能

支持 13 种转换组合：

| 源 \\ 目标 | Excel | Word | Markdown |
|-----------|-------|------|----------|
| **PDF**   | ✅    | ✅   | ✅       |
| **Excel** | —     | ✅   | ✅       |
| **Word**  | ✅    | —    | ✅       |
| **Markdown** | ✅ | ✅   | —        |
| **ZIP (HTML→MD)** | — | — | ✅ |

> **→PDF** 的转换（Excel→PDF、Word→PDF、Markdown→PDF）需要系统已安装 **Microsoft Word** 或 **LibreOffice**。
>
> **ZIP→MD** 转换适用于浏览器 **Ctrl+S** 保存的「网页完整保存」格式（`.htm` + `_files/` 资源目录），打包为 ZIP 后拖入工具即可。

## 使用方式

### 方式一：直接运行（需 Python 3.10+）

```bash
pip install -r requirements.txt
python main.py
```

### 方式二：打包 exe

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "文件转换工具" --add-data "converters;converters" main.py
```

打包后在 `dist/文件转换工具.exe`，双击运行。

## 项目结构

```
FileConverter/
├── main.py                    # 应用入口，启动 Tkinter 窗口
├── converters/                # 格式转换核心逻辑
│   ├── __init__.py            # 转换注册表与调度入口
│   ├── pdf_converter.py       # PDF 输入转换到 Excel/Word/Markdown
│   ├── excel_converter.py     # Excel 输入转换到 PDF/Word/Markdown
│   ├── word_converter.py      # Word 输入转换到 PDF/Excel/Markdown
│   ├── markdown_converter.py  # Markdown 输入转换到 PDF/Excel/Word
│   ├── html_converter.py      # ZIP (HTML) 输入转换到 Markdown
│   └── pdf_export.py          # 统一 docx -> PDF 导出工具
├── ui/
│   └── main_window.py         # Tkinter 主窗口与批量转换界面
├── requirements.txt           # 依赖列表
└── README.md                  # 项目说明文档
```

## 技术栈

- **Python** 3.13
- **tkinter** — 界面
- **pdfplumber** — PDF 解析
- **openpyxl** — Excel 读写
- **python-docx** — Word 读写
- **beautifulsoup4** — HTML 解析