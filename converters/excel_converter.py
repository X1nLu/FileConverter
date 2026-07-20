from pathlib import Path
from openpyxl import load_workbook
from .pdf_export import docx_to_pdf


class ExcelConverter:

    @staticmethod
    def to_pdf(xlsx_path: str, pdf_path: str):
        from docx import Document

        wb = load_workbook(xlsx_path)
        doc = Document()

        for ws in wb.worksheets:
            doc.add_heading(ws.title, level=2)
            table_data = []
            for row in ws.iter_rows(values_only=True):
                table_data.append([str(c) if c else "" for c in row])

            if table_data:
                table = doc.add_table(rows=len(table_data), cols=len(table_data[0]), style="Table Grid")
                for i, row_data in enumerate(table_data):
                    for j, cell_val in enumerate(row_data):
                        if j < len(table_data[0]):
                            table.cell(i, j).text = cell_val

            doc.add_paragraph()

        temp_docx = str(Path(pdf_path).with_suffix(".docx"))
        doc.save(temp_docx)

        docx_to_pdf(temp_docx, pdf_path, "Excel -> PDF 需安装 MS Word (Windows) 或 LibreOffice (Linux/Mac)")
        Path(temp_docx).unlink(missing_ok=True)

    @staticmethod
    def to_word(xlsx_path: str, docx_path: str):
        from docx import Document
        from docx.shared import Inches, Pt

        wb = load_workbook(xlsx_path)
        doc = Document()

        for ws in wb.worksheets:
            doc.add_heading(ws.title, level=2)
            table_data = []
            column_widths = []
            for row in ws.iter_rows(values_only=True):
                table_data.append([str(c) if c else "" for c in row])
                if not column_widths:
                    column_widths = [Inches(1.5)] * len(row)

            if table_data:
                table = doc.add_table(rows=len(table_data), cols=len(table_data[0]), style="Table Grid")
                for i, row_data in enumerate(table_data):
                    for j, cell_val in enumerate(row_data):
                        if j < len(table_data[0]):
                            table.cell(i, j).text = cell_val
                doc.add_paragraph()

        doc.save(docx_path)

    @staticmethod
    def to_markdown(xlsx_path: str, md_path: str):
        wb = load_workbook(xlsx_path)
        lines = []

        for ws in wb.worksheets:
            lines.append(f"## {ws.title}\n")
            table_data = []
            for row in ws.iter_rows(values_only=True):
                table_data.append([str(c) if c else "" for c in row])

            if table_data:
                header = table_data[0]
                lines.append("| " + " | ".join(header) + " |")
                lines.append("|" + "|".join("---" for _ in header) + "|")
                for row in table_data[1:]:
                    lines.append("| " + " | ".join(row) + " |")
            else:
                lines.append("（本 Sheet 无内容）")
            lines.append("")

        Path(md_path).write_text("\n".join(lines), encoding="utf-8")