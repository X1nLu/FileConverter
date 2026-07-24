import os
import re
import shutil
import zipfile
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup, Tag


class HtmlConverter:
    """Convert browser Ctrl+S saved HTML (packed as ZIP) to Markdown."""

    # Attachment extensions to extract to _assets/ directory
    ASSET_EXTENSIONS = {
        # Images
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".ico",
        # Documents
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        # Others
        ".zip", ".rar", ".7z", ".csv", ".txt",
    }

    @staticmethod
    def to_markdown(zip_path: str, md_path: str, on_progress=None):
        """Convert HTML from ZIP package to Markdown."""
        md_path = Path(md_path)
        md_path.parent.mkdir(parents=True, exist_ok=True)

        # Assets directory (only created when there are images or attachments)
        assets_dir = md_path.parent / f"{md_path.stem}_assets"
        has_assets = False

        with zipfile.ZipFile(zip_path, "r") as z:
            # Find HTML file
            html_name = HtmlConverter._find_html_file(z)
            html_content = z.read(html_name).decode("utf-8", errors="replace")

            # Parse HTML
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract title as MD filename (if not specified)
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""

            # Remove unwanted elements
            HtmlConverter._remove_unwanted(soup)

            # Find content area (prefer container/main/article, fallback to body)
            body = HtmlConverter._find_content_area(soup)

            # Convert content to MD
            md_lines = []
            asset_map = {}  # original path -> new filename

            if title:
                md_lines.append(f"# {title}")
                md_lines.append("")

            for element in body.children:
                if not isinstance(element, Tag):
                    continue
                HtmlConverter._convert_element(
                    element, md_lines, z, html_name, assets_dir, asset_map
                )

            # Extract asset files
            if asset_map:
                has_assets = True
                assets_dir.mkdir(parents=True, exist_ok=True)
                HtmlConverter._extract_assets(z, asset_map, assets_dir)

            # Write MD file
            md_text = "\n".join(md_lines)
            # Clean up extra blank lines
            md_text = re.sub(r"\n{3,}", "\n\n", md_text)
            md_text = md_text.strip() + "\n"
            md_path.write_text(md_text, encoding="utf-8")

        # If no assets, delete empty directory
        if not has_assets and assets_dir.exists():
            try:
                assets_dir.rmdir()
            except OSError:
                pass

    # ------------------------------------------------------------------ #
    #  Internal methods
    # ------------------------------------------------------------------ #

    @staticmethod
    def _find_html_file(z: zipfile.ZipFile) -> str:
        """Find HTML file in ZIP."""
        html_candidates = []
        for name in z.namelist():
            lower = name.lower()
            if lower.endswith(".htm") or lower.endswith(".html"):
                # Prefer HTML not in _files subdirectory (i.e., top-level)
                if "/" not in name or not any(
                    part.endswith("_files") for part in name.split("/")
                ):
                    html_candidates.insert(0, name)
                else:
                    html_candidates.append(name)
        if not html_candidates:
            raise ValueError("No HTML file found in ZIP")
        return html_candidates[0]

    @staticmethod
    def _remove_unwanted(soup: BeautifulSoup):
        """Remove unwanted elements."""
        for tag in soup.find_all(["script", "style", "noscript", "iframe", "meta", "link"]):
            tag.decompose()

    @staticmethod
    def _find_content_area(soup: BeautifulSoup) -> Tag:
        """Find content area."""
        # Prefer common content containers
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
        """Recursively convert HTML elements to MD."""
        tag = element.name
        if not tag:
            # Text node
            text = element.get_text(strip=True)
            if text:
                md_lines.append(text)
            return

        # Process by tag
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
            # Try to detect language
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
            # Handle attachment links inside ZIP
            if "_files/" in href and not href.startswith("http"):
                # This is an attachment inside ZIP
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
            # Detect special class
            classes = element.get("class", [])
            if not isinstance(classes, list):
                classes = []

            class_set = set(classes)

            # Flowchart / diagram
            if "diagram" in class_set or "flow-row" in class_set:
                md_lines.append("```text")
                text = HtmlConverter._get_diagram_text(element)
                md_lines.append(text)
                md_lines.append("```")
                md_lines.append("")
                return

            # Callout - use plain text to avoid conflict with prefix **
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

            # Regular div - recurse children
            for child in element.children:
                if isinstance(child, Tag):
                    HtmlConverter._convert_element(
                        child, md_lines, z, html_name, assets_dir, asset_map
                    )

        elif tag == "span":
            classes = element.get("class", [])
            if not isinstance(classes, list):
                classes = []
            # flow-box tag
            if any("flow-box" in (c or "") for c in classes):
                text = element.get_text(strip=True)
                if text:
                    md_lines.append(f"`{text}`")
            else:
                text = HtmlConverter._get_inner_text(element)
                if text:
                    md_lines.append(text)

        elif tag == "header":
            # Skip header (already handled by title)
            pass

        elif tag == "footer":
            # Skip footer
            pass

        elif tag == "nav":
            # Skip navigation
            pass

        elif tag in ("section", "article", "main"):
            for child in element.children:
                if isinstance(child, Tag):
                    HtmlConverter._convert_element(
                        child, md_lines, z, html_name, assets_dir, asset_map
                    )

        else:
            # Other tags - recurse
            for child in element.children:
                if isinstance(child, Tag):
                    HtmlConverter._convert_element(
                        child, md_lines, z, html_name, assets_dir, asset_map
                    )

    @staticmethod
    def _convert_table(element: Tag, md_lines: list):
        """Convert HTML table to MD table."""
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

        # Align column count
        max_cols = max(len(r) for r in table_data)
        table_data = [r + [""] * (max_cols - len(r)) for r in table_data]

        # Table header
        header = table_data[0]
        md_lines.append("| " + " | ".join(header) + " |")
        md_lines.append("|" + "|".join("---" for _ in header) + "|")

        # Table body
        for row in table_data[1:]:
            md_lines.append("| " + " | ".join(row) + " |")

        md_lines.append("")

    @staticmethod
    def _get_inner_text(element: Tag) -> str:
        """Get element plain text, handling inline elements."""
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
        """Get plain text without MD formatting (for callouts and other semantic containers)."""
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
                    # strong, em, and other tags - plain text only
                    parts.append(child.get_text(strip=True))
            else:
                text = str(child).strip()
                if text:
                    parts.append(text)
        return "".join(parts)

    @staticmethod
    def _get_diagram_text(element: Tag) -> str:
        """Extract flowchart/diagram text representation."""
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
        """Convert relative resource path in HTML to absolute path within ZIP."""
        # If already absolute path (relative to ZIP root)
        if not orig_path.startswith(".."):
            # May be relative to HTML file path
            html_dir = os.path.dirname(html_name)
            if html_dir:
                # Remove possible ../ prefix
                clean = orig_path.replace("\\", "/")
                if clean.startswith("../"):
                    # Relative to ZIP root
                    return os.path.normpath(clean.lstrip("../"))
                else:
                    return os.path.normpath(f"{html_dir}/{clean}")
        return os.path.normpath(orig_path)

    @staticmethod
    def _generate_asset_name(asset_key: str, asset_map: dict) -> str:
        """Generate unique filename for asset."""
        # If mapping already exists, return directly
        if asset_key in asset_map:
            return asset_map[asset_key]

        # Generate new name
        basename = os.path.basename(asset_key)
        if basename:
            # Check for duplicate name
            existing_names = set(asset_map.values())
            if basename not in existing_names:
                return basename
            # Add suffix if duplicate
            stem, ext = os.path.splitext(basename)
            counter = 1
            while f"{stem}_{counter}{ext}" in existing_names:
                counter += 1
            return f"{stem}_{counter}{ext}"

        # No filename, use hash
        stem = f"asset_{len(asset_map)}"
        return stem

    @staticmethod
    def _extract_assets(
        z: zipfile.ZipFile,
        asset_map: dict,
        assets_dir: Path,
    ):
        """Extract resource files from ZIP to assets directory."""
        for orig_path, new_name in asset_map.items():
            try:
                # Try multiple paths
                candidates = HtmlConverter._find_asset_in_zip(z, orig_path)
                if candidates:
                    # Use first match
                    zip_path = candidates[0]
                    data = z.read(zip_path)
                    dest = assets_dir / new_name
                    dest.write_bytes(data)
            except Exception:
                # Skip unextractable resources
                pass

    @staticmethod
    def _find_asset_in_zip(z: zipfile.ZipFile, orig_path: str) -> list:
        """Find resource file in ZIP (try multiple path variants)."""
        candidates = []
        norm = orig_path.replace("\\", "/")

        # Exact match
        if norm in z.namelist():
            candidates.append(norm)

        # Match by filename
        basename = os.path.basename(norm)
        for name in z.namelist():
            if name.endswith(f"/{basename}") or name.endswith(f"\\{basename}"):
                if name not in candidates:
                    candidates.append(name)

        # Fuzzy match (URL encoding, etc.)
        unquoted = unquote(norm)
        if unquoted != norm:
            for name in z.namelist():
                if unquoted in name or name in unquoted:
                    if name not in candidates:
                        candidates.append(name)

        return candidates