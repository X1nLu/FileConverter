from pathlib import Path


class MarkdownConverter:

    @staticmethod
    def to_pdf(md_path: str, pdf_path: str):
        from docx import Document
        from docx.shared import Pt

        doc = Document()
        text = Path(md_path).read_text(encoding="utf-8")

        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("## "):
                doc.add_heading(stripped[3:], level=2)
            elif stripped.startswith("# "):
                doc.add_heading(stripped[2:], level=1)
            elif "|" in stripped and stripped.startswith("|"):
                continue
            elif stripped.startswith("|---"):
                continue
            elif stripped:
                p = doc.add_paragraph(stripped)
                for run in p.runs:
                    run.font.size = Pt(10)

        temp_docx = str(Path(pdf_path).with_suffix(".docx"))
        doc.save(temp_docx)

        try:
            import subprocess, sys
            if sys.platform == "win32":
                import win32com.client
                word = win32com.client.Dispatch("Word.Application")
                word.Visible = False
                wd = word.Documents.Open(temp_docx)
                wd.SaveAs(pdf_path, FileFormat=17)
                wd.Close()
                word.Quit()
            else:
                subprocess.run(
                    ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir",
                     str(Path(pdf_path).parent), temp_docx],
                    check=True, capture_output=True
                )
        except Exception:
            raise RuntimeError("Markdown -> PDF 需安装 MS Word (Windows) 或 LibreOffice (Linux/Mac)")
        finally:
            Path(temp_docx).unlink(missing_ok=True)

    @staticmethod
    def to_excel(md_path: str, xlsx_path: str):
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "Markdown内容"

        text = Path(md_path).read_text(encoding="utf-8")
        row_idx = 1

        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                if not any("---" in c for c in cells):
                    for col_idx, cell in enumerate(cells, start=1):
                        ws.cell(row=row_idx, column=col_idx, value=cell)
                    row_idx += 1
            elif stripped:
                ws.cell(row=row_idx, column=1, value=stripped)
                row_idx += 1

        wb.save(xlsx_path)

    @staticmethod
    def to_word(md_path: str, docx_path: str):
        from docx import Document
        from docx.shared import Pt

        doc = Document()
        text = Path(md_path).read_text(encoding="utf-8")

        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("## "):
                doc.add_heading(stripped[3:], level=2)
            elif stripped.startswith("# "):
                doc.add_heading(stripped[2:], level=1)
            elif "|" in stripped and stripped.startswith("|"):
                continue
            elif stripped.startswith("|---"):
                continue
            elif stripped:
                p = doc.add_paragraph(stripped)
                for run in p.runs:
                    run.font.size = Pt(10)

        doc.save(docx_path)