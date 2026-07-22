from pathlib import Path
from docx import Document
from .pdf_export import docx_to_pdf


class WordConverter:

    @staticmethod
    def to_pdf(docx_path: str, pdf_path: str):
        docx_to_pdf(docx_path, pdf_path, "Word -> PDF requires MS Word (Windows) or LibreOffice (Linux/Mac)")

    @staticmethod
    def to_excel(docx_path: str, xlsx_path: str):
        from openpyxl import Workbook

        doc = Document(docx_path)
        wb = Workbook()
        ws = wb.active
        ws.title = "Document Content"

        row_idx = 1
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                ws.cell(row=row_idx, column=1, value=text)
                row_idx += 1

        for i, table in enumerate(doc.tables):
            row_idx += 1
            ws.cell(row=row_idx, column=1, value=f"[Table {i+1}]")
            row_idx += 1
            for row in table.rows:
                for j, cell in enumerate(row.cells):
                    ws.cell(row=row_idx, column=j + 1, value=cell.text)
                row_idx += 1

        wb.save(xlsx_path)

    @staticmethod
    def to_markdown(docx_path: str, md_path: str):
        doc = Document(docx_path)
        lines = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            style = para.style.name
            if "Heading 1" in style:
                lines.append(f"# {text}")
            elif "Heading 2" in style:
                lines.append(f"## {text}")
            elif "Heading 3" in style:
                lines.append(f"### {text}")
            else:
                lines.append(text)
            lines.append("")

        for i, table in enumerate(doc.tables):
            lines.append(f"**Table {i+1}**\n")
            table_data = [[cell.text for cell in row.cells] for row in table.rows]
            if table_data:
                header = table_data[0]
                lines.append("| " + " | ".join(header) + " |")
                lines.append("|" + "|".join("---" for _ in header) + "|")
                for row in table_data[1:]:
                    lines.append("| " + " | ".join(row) + " |")
            lines.append("")

        Path(md_path).write_text("\n".join(lines), encoding="utf-8")