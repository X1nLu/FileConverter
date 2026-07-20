import subprocess
import sys
from pathlib import Path


def docx_to_pdf(docx_path: str, pdf_path: str, error_message: str):
    """将 .docx 转为 PDF，支持 Windows Word 和 LibreOffice。"""
    try:
        if sys.platform == "win32":
            import win32com.client

            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            wd = word.Documents.Open(str(Path(docx_path).resolve()))
            wd.SaveAs(str(Path(pdf_path).resolve()), FileFormat=17)
            wd.Close()
            word.Quit()
        else:
            subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(Path(pdf_path).parent.resolve()),
                    str(Path(docx_path).resolve()),
                ],
                check=True,
                capture_output=True,
            )
    except Exception as exc:
        raise RuntimeError(f"{error_message}: {exc}") from exc
