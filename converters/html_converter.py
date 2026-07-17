import os
import re
import shutil
import zipfile
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup, Tag


class HtmlConverter:
    """将浏览器 Ctrl+S 保存的 HTML (打包为 ZIP) 转换为 Markdown。"""

    # 需要提取到 _assets/ 目录的附件扩展名
    ASSET_EXTENSIONS = {
        # 图片
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".ico",
        # 文档
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        # 其他
        ".zip", ".rar", ".7z", ".csv", ".txt",
    }

    @staticmethod
    def to_markdown(zip_path: str, md_path: str):
        """将 ZIP 包中的 HTML 转换为 Markdown。"""
        md_path = Path(md_path)
        md_path.parent.mkdir(parents=True, exist_ok=True)

        # 资源目录（仅当有图片或附件时创建）
        assets_dir = md_path.parent / f"{md_path.stem}_assets"
        has_assets = False

        with zipfile.ZipFile(zip_path, "r") as z:
            # 找到 HTML 文件
            html_name = HtmlConverter._find_html_file(z)
            html_content = z.read(html_name).decode("utf-8", errors="replace")

            # 解析 HTML
            soup = BeautifulSoup(html_content, "html.parser")

            # 提取标题作为 MD 文件名（如果未指定）
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""

            # 移除不需要的元素
            HtmlConverter._remove_unwanted(soup)

            # 找到正文区域（优先 container/main/article，否则用 body）
            body = HtmlConverter._find_content_area(soup)

            # 转换正文为 MD
            md_lines = []
            asset_map = {}  # 原始路径 -> 新文件名

            if title:
                md_lines.append(f"# {title}")
                md_lines.append("")

            for element in body.children:
                if not isinstance(element, Tag):
                    continue
                HtmlConverter._convert_element(
                    element, md_lines, z, html_name, assets_dir, asset_map
                )

            # 提取资源文件
            if asset_map:
                has_assets = True
                assets_dir.mkdir(parents=True, exist_ok=True)
                HtmlConverter._extract_assets(z, asset_map, assets_dir)

            # 写入 MD 文件
            md_text = "\n".join(md_lines)
            # 清理多余空行
            md_text = re.sub(r"\n{3,}", "\n\n", md_text)
            md_text = md_text.strip() + "\n"
            md_path.write_text(md_text, encoding="utf-8")

        # 如果没有资源文件，删除空目录
        if not has_assets and assets_dir.exists():
            try:
                assets_dir.rmdir()
            except OSError:
                pass

    # ------------------------------------------------------------------ #
    #  内部方法
    # ------------------------------------------------------------------ #

    @staticmethod
    def _find_html_file(z: zipfile.ZipFile) -> str:
        """在 ZIP 中找到 HTML 文件。"""
        html_candidates = []
        for name in z.namelist():
            lower = name.lower()
            if lower.endswith(".htm") or lower.endswith(".html"):
                # 优先选择不在 _files 子目录中的（即顶层 HTML）
                if "/" not in name or not any(
                    part.endswith("_files") for part in name.split("/")
                ):
                    html_candidates.insert(0, name)
                else:
                    html_candidates.append(name)
        if not html_candidates:
            raise ValueError("ZIP 文件中未找到 HTML 文件")
        return html_candidates[0]

    @staticmethod
    def _remove_unwanted(soup: BeautifulSoup):
        """移除不需要的元素。"""
        for tag in soup.find_all(["script", "style", "noscript", "iframe", "meta", "link"]):
            tag.decompose()

    @staticmethod
    def _find_content_area(soup: BeautifulSoup) -> Tag:
        """找到正文区域。"""
        # 优先用常见的内容容器
        for selector in [
            "div.container", "main", "article",
            ".content", ".post", ".article", ".doc-content",
            "body",
        ]:
            area = soup.select_one(selector)
            if area:
                return area
        return soup.body or soup

    @staticmethod
    def _convert_element(
        element: Tag,
        md_lines: list,
        z: zipfile.ZipFile,
        html_name: str,
        assets_dir: Path,
        asset_map: dict,
    ):
        """递归转换 HTML 元素为 MD。"""
        tag = element.name
        if not tag:
            # 纯文本节点
            text = element.get_text(strip=True)
            if text:
                md_lines.append(text)
            return

        # 根据标签处理
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            text = HtmlConverter._get_inner_text(element)
            if text:
                md_lines.append(f"{'#' * level} {text}")
                md_lines.append("")

        elif tag == "p":
            text = HtmlConverter._get_inner_text(element)
            if text:
                md_lines.append(text)
                md_lines.append("")

        elif tag in ("ul", "ol"):
            for i, li in enumerate(element.find_all("li", recursive=False)):
                prefix = "- " if tag == "ul" else f"{i + 1}. "
                text = HtmlConverter._get_inner_text(li)
                if text:
                    md_lines.append(f"{prefix}{text}")
            md_lines.append("")

        elif tag == "blockquote":
            text = HtmlConverter._get_inner_text(element)
            if text:
                for line in text.split("\n"):
                    md_lines.append(f"> {line}")
                md_lines.append("")

        elif tag == "table":
            HtmlConverter._convert_table(element, md_lines)

        elif tag == "pre":
            code_tag = element.find("code")
            code_text = code_tag.get_text() if code_tag else element.get_text()
            # 尝试检测语言
            lang = ""
            if code_tag and code_tag.get("class"):
                classes = code_tag.get("class")
                for cls in classes:
                    if cls.startswith("language-"):
                        lang = cls.replace("language-", "")
                        break
            md_lines.append(f"```{lang}")
            md_lines.append(code_text.rstrip("\n"))
            md_lines.append("```")
            md_lines.append("")

        elif tag == "code":
            text = element.get_text(strip=True)
            if text:
                md_lines.append(f"`{text}`")

        elif tag in ("strong", "b"):
            text = HtmlConverter._get_inner_text(element)
            if text:
                md_lines.append(f"**{text}**")

        elif tag in ("em", "i"):
            text = HtmlConverter._get_inner_text(element)
            if text:
                md_lines.append(f"*{text}*")

        elif tag == "a":
            href = element.get("href", "")
            text = HtmlConverter._get_inner_text(element) or href
            # 处理 ZIP 内的附件链接
            if "_files/" in href and not href.startswith("http"):
                # 这是 ZIP 内的附件
                orig_path = unquote(href)
                asset_key = HtmlConverter._normalize_asset_path(orig_path, html_name)
                new_name = HtmlConverter._generate_asset_name(asset_key, asset_map)
                asset_map[asset_key] = new_name
                md_lines.append(f"[{text}]({assets_dir.name}/{new_name})")
            elif href:
                md_lines.append(f"[{text}]({href})")
            else:
                md_lines.append(text)

        elif tag == "img":
            src = element.get("src", "")
            alt = element.get("alt", "") or ""
            if "_files/" in src:
                orig_path = unquote(src)
                asset_key = HtmlConverter._normalize_asset_path(orig_path, html_name)
                ext = os.path.splitext(asset_key)[1].lower()
                new_name = HtmlConverter._generate_asset_name(asset_key, asset_map)
                asset_map[asset_key] = new_name
                md_lines.append(f"![{alt}]({assets_dir.name}/{new_name})")
            elif src.startswith(("http://", "https://")):
                md_lines.append(f"![{alt}]({src})")
            md_lines.append("")

        elif tag == "hr":
            md_lines.append("---")
            md_lines.append("")

        elif tag == "div":
            # 检测特殊 class
            classes = element.get("class", [])
            if not isinstance(classes, list):
                classes = []

            class_set = set(classes)

            # 流程图 / diagram
            if "diagram" in class_set or "flow-row" in class_set:
                md_lines.append("```text")
                text = HtmlConverter._get_diagram_text(element)
                md_lines.append(text)
                md_lines.append("```")
                md_lines.append("")
                return

            # 提示框 — 用纯文本避免与 prefix 的 ** 冲突
            if "insight" in class_set:
                prefix = "> "
                if "insight-success" in class_set:
                    prefix = "> **✅** "
                elif "insight-warning" in class_set:
                    prefix = "> **⚠️** "
                else:
                    prefix = "> **💡** "
                text = HtmlConverter._get_plain_text(element)
                for line in text.split("\n"):
                    line = line.strip()
                    if line:
                        md_lines.append(f"{prefix}{line}")
                md_lines.append("")
                return

            # 普通 div — 递归子元素
            for child in element.children:
                if isinstance(child, Tag):
                    HtmlConverter._convert_element(
                        child, md_lines, z, html_name, assets_dir, asset_map
                    )

        elif tag == "span":
            classes = element.get("class", [])
            if not isinstance(classes, list):
                classes = []
            # flow-box 标签
            if any("flow-box" in (c or "") for c in classes):
                text = element.get_text(strip=True)
                if text:
                    md_lines.append(f"`{text}`")
            else:
                text = HtmlConverter._get_inner_text(element)
                if text:
                    md_lines.append(text)

        elif tag == "header":
            # 跳过 header（已有 title 处理）
            pass

        elif tag == "footer":
            # 跳过 footer
            pass

        elif tag == "nav":
            # 跳过导航
            pass

        elif tag in ("section", "article", "main"):
            for child in element.children:
                if isinstance(child, Tag):
                    HtmlConverter._convert_element(
                        child, md_lines, z, html_name, assets_dir, asset_map
                    )

        else:
            # 其他标签 — 递归
            for child in element.children:
                if isinstance(child, Tag):
                    HtmlConverter._convert_element(
                        child, md_lines, z, html_name, assets_dir, asset_map
                    )

    @staticmethod
    def _convert_table(element: Tag, md_lines: list):
        """转换 HTML 表格为 MD 表格。"""
        rows = element.find_all("tr")
        if not rows:
            return

        table_data = []
        for row in rows:
            cells = []
            for cell in row.find_all(["th", "td"]):
                text = cell.get_text(strip=True)
                cells.append(text)
            if cells:
                table_data.append(cells)

        if not table_data:
            return

        # 对齐列数
        max_cols = max(len(r) for r in table_data)
        table_data = [r + [""] * (max_cols - len(r)) for r in table_data]

        # 表头
        header = table_data[0]
        md_lines.append("| " + " | ".join(header) + " |")
        md_lines.append("|" + "|".join("---" for _ in header) + "|")

        # 表体
        for row in table_data[1:]:
            md_lines.append("| " + " | ".join(row) + " |")

        md_lines.append("")

    @staticmethod
    def _get_inner_text(element: Tag) -> str:
        """获取元素的纯文本，处理行内元素。"""
        parts = []
        for child in element.children:
            if isinstance(child, Tag):
                tag = child.name
                if tag == "br":
                    parts.append("\n")
                elif tag == "code":
                    parts.append(f"`{child.get_text(strip=True)}`")
                elif tag in ("strong", "b"):
                    parts.append(f"**{child.get_text(strip=True)}**")
                elif tag in ("em", "i"):
                    parts.append(f"*{child.get_text(strip=True)}*")
                elif tag == "a":
                    href = child.get("href", "")
                    text = child.get_text(strip=True) or href
                    if href:
                        parts.append(f"[{text}]({href})")
                    else:
                        parts.append(text)
                elif tag == "img":
                    alt = child.get("alt", "") or ""
                    src = child.get("src", "")
                    if src:
                        parts.append(f"![{alt}]({src})")
                    else:
                        parts.append(alt)
                elif tag == "span":
                    parts.append(HtmlConverter._get_inner_text(child))
                else:
                    parts.append(child.get_text(strip=True))
            else:
                text = str(child).strip()
                if text:
                    parts.append(text)
        return "".join(parts)

    @staticmethod
    def _get_plain_text(element: Tag) -> str:
        """获取纯文本，不添加任何 MD 格式标记（用于 insight 等已有语义容器的内部文本）。"""
        parts = []
        for child in element.children:
            if isinstance(child, Tag):
                tag = child.name
                if tag == "br":
                    parts.append("\n")
                elif tag == "code":
                    parts.append(f"`{child.get_text(strip=True)}`")
                elif tag == "a":
                    href = child.get("href", "")
                    text = child.get_text(strip=True) or href
                    if href:
                        parts.append(f"[{text}]({href})")
                    else:
                        parts.append(text)
                elif tag == "img":
                    alt = child.get("alt", "") or ""
                    src = child.get("src", "")
                    if src:
                        parts.append(f"![{alt}]({src})")
                    else:
                        parts.append(alt)
                elif tag == "span":
                    parts.append(HtmlConverter._get_plain_text(child))
                else:
                    # strong, em, 及其他标签 — 只取纯文本
                    parts.append(child.get_text(strip=True))
            else:
                text = str(child).strip()
                if text:
                    parts.append(text)
        return "".join(parts)

    @staticmethod
    def _get_diagram_text(element: Tag) -> str:
        """提取流程图/图表的文本表示。"""
        lines = []
        for child in element.find_all(["div", "span"], recursive=True):
            text = child.get_text(strip=True)
            classes = child.get("class", []) or []
            if text:
                if any("flow-box" in (c or "") for c in classes):
                    lines.append(f"[{text}]")
                elif any("flow-arrow" in (c or "") for c in classes):
                    lines.append(f" {text} ")
                else:
                    lines.append(text)
        return "\n".join(lines)

    @staticmethod
    def _normalize_asset_path(orig_path: str, html_name: str) -> str:
        """将 HTML 中的相对资源路径转为 ZIP 内的绝对路径。"""
        # 如果已经是绝对路径（相对 ZIP 根）
        if not orig_path.startswith(".."):
            # 可能是相对 HTML 文件的路径
            html_dir = os.path.dirname(html_name)
            if html_dir:
                # 去掉可能的 ../ 前缀
                clean = orig_path.replace("\\", "/")
                if clean.startswith("../"):
                    # 相对于 ZIP 根
                    return os.path.normpath(clean.lstrip("../"))
                else:
                    return os.path.normpath(f"{html_dir}/{clean}")
        return os.path.normpath(orig_path)

    @staticmethod
    def _generate_asset_name(asset_key: str, asset_map: dict) -> str:
        """为资源生成唯一文件名。"""
        # 如果已存在映射，直接返回
        if asset_key in asset_map:
            return asset_map[asset_key]

        # 生成新名称
        basename = os.path.basename(asset_key)
        if basename:
            # 检查是否重名
            existing_names = set(asset_map.values())
            if basename not in existing_names:
                return basename
            # 重名加后缀
            stem, ext = os.path.splitext(basename)
            counter = 1
            while f"{stem}_{counter}{ext}" in existing_names:
                counter += 1
            return f"{stem}_{counter}{ext}"

        # 无文件名，用 hash
        stem = f"asset_{len(asset_map)}"
        return stem

    @staticmethod
    def _extract_assets(
        z: zipfile.ZipFile,
        asset_map: dict,
        assets_dir: Path,
    ):
        """从 ZIP 中提取资源文件到 assets 目录。"""
        for orig_path, new_name in asset_map.items():
            try:
                # 尝试多种路径
                candidates = HtmlConverter._find_asset_in_zip(z, orig_path)
                if candidates:
                    # 使用第一个匹配
                    zip_path = candidates[0]
                    data = z.read(zip_path)
                    dest = assets_dir / new_name
                    dest.write_bytes(data)
            except Exception:
                # 跳过无法提取的资源
                pass

    @staticmethod
    def _find_asset_in_zip(z: zipfile.ZipFile, orig_path: str) -> list:
        """在 ZIP 中查找资源文件（尝试多种路径变体）。"""
        candidates = []
        norm = orig_path.replace("\\", "/")

        # 精确匹配
        if norm in z.namelist():
            candidates.append(norm)

        # 按文件名匹配
        basename = os.path.basename(norm)
        for name in z.namelist():
            if name.endswith(f"/{basename}") or name.endswith(f"\\{basename}"):
                if name not in candidates:
                    candidates.append(name)

        # 模糊匹配（URL 编码等）
        unquoted = unquote(norm)
        if unquoted != norm:
            for name in z.namelist():
                if unquoted in name or name in unquoted:
                    if name not in candidates:
                        candidates.append(name)

        return candidates