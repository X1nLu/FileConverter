from .pdf_converter import PdfConverter
from .excel_converter import ExcelConverter
from .word_converter import WordConverter
from .markdown_converter import MarkdownConverter
from .html_converter import HtmlConverter

REGISTRY = {
    ("pdf", "xlsx"): PdfConverter.to_excel,
    ("pdf", "docx"): PdfConverter.to_word,
    ("pdf", "md"):   PdfConverter.to_markdown,
    ("xlsx", "pdf"): ExcelConverter.to_pdf,
    ("xlsx", "docx"): ExcelConverter.to_word,
    ("xlsx", "md"):  ExcelConverter.to_markdown,
    ("docx", "pdf"): WordConverter.to_pdf,
    ("docx", "xlsx"): WordConverter.to_excel,
    ("docx", "md"):  WordConverter.to_markdown,
    ("md", "pdf"):   MarkdownConverter.to_pdf,
    ("md", "xlsx"):  MarkdownConverter.to_excel,
    ("md", "docx"):  MarkdownConverter.to_word,
    ("zip", "md"):   HtmlConverter.to_markdown,
}

def get_supported_conversions():
    return list(REGISTRY.keys())

def convert(input_path: str, output_path: str, from_ext: str, to_ext: str):
    fn = REGISTRY.get((from_ext, to_ext))
    if fn is None:
        raise ValueError(f"不支持的转换: {from_ext} -> {to_ext}")
    fn(input_path, output_path)