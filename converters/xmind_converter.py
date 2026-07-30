import os
from pathlib import Path
from typing import Callable, Optional

from . import xmind2pdf


class XMindConverter:

    @staticmethod
    def to_pdf(
        xmind_path: str,
        pdf_path: str,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ):
        if on_progress:
            on_progress(0, 1)

        if not os.path.isfile(xmind_path):
            raise FileNotFoundError(xmind_path)

        sheets = xmind2pdf.parse_xmind(xmind_path)
        if not sheets:
            raise ValueError("No mind map content found in XMind file")

        Path(pdf_path).parent.mkdir(parents=True, exist_ok=True)
        xmind2pdf.render_pdf(sheets, pdf_path)

        if on_progress:
            on_progress(1, 1)
