"""
Generate a PDF report from a Markdown string and optional image files.
Requires: pip install fpdf2
"""
import os
from configs.app_config import APP_DISPLAY
import re
from datetime import datetime
from fpdf import FPDF

# ── CJK font auto-discovery ───────────────────────────────────────────────────
_CJK_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    "/usr/share/fonts/wenquanyi/wqy-microhei/wqy-microhei.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
]


def _find_cjk_font() -> str | None:
    for p in _CJK_FONT_CANDIDATES:
        if os.path.isfile(p):
            return p
    return None


def _has_cjk(text: str) -> bool:
    return any("一" <= c <= "鿿" for c in text)


# Characters not in Latin-1 (ISO 8859-1) that commonly appear in LLM output
_LATIN1_SUBS: dict[str, str] = {
    "‘": "'",   "’": "'",    # curly single quotes
    "“": '"',   "”": '"',    # curly double quotes
    "–": "-",   "—": "--",   # en/em dash
    "…": "...", "·": ".",    # ellipsis, middle dot
    "•": "*",   "‣": ">",    # bullet, triangular bullet
    "●": "*",   "◦": "*",    # black/white circle
    "‐": "-",   "−": "-",    # hyphen, minus sign
    "×": "x",   "°": "deg", # multiplication, degree
    "α": "alpha", "β": "beta", "γ": "gamma",
}


def _sanitize_latin1(text: str) -> str:
    for src, dst in _LATIN1_SUBS.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def _strip_emoji(text: str) -> str:
    return re.sub(
        r"[\U00010000-\U0010ffff"
        r"\U0001F300-\U0001F9FF"
        r"☀-⛿✀-➿]",
        "",
        text,
    ).strip()


class _ReportPDF(FPDF):
    def __init__(self, lang: str = "en_US"):
        super().__init__()
        self._lang = lang
        self._body_font = "Helvetica"

    def header(self):
        font = self._body_font
        self.set_font(font, "B", 9)
        self.set_text_color(76, 139, 245)
        if self._lang == "en_US":
            label = f"{APP_DISPLAY} Analysis Report"
        else:
            label = _sanitize_latin1(f"{APP_DISPLAY} Analysis Report") if font == "Helvetica" else f"{APP_DISPLAY} 分析报告"
        self.cell(0, 7, label, align="R")
        self.ln(2)
        self.set_draw_color(76, 139, 245)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(160, 160, 160)
        self.cell(0, 8, f"Page {self.page_no()} / {{nb}}", align="C")


def _safe_cell(pdf: _ReportPDF, h: float, text: str) -> None:
    """multi_cell with guaranteed left-margin reset and fallback for empty text."""
    pdf.set_x(pdf.l_margin)
    if not text.strip():
        pdf.ln(h)
        return
    try:
        pdf.multi_cell(0, h, text)
    except Exception:
        # Last resort: truncate to something that fits
        pdf.multi_cell(0, h, text[:80] + "...")


def _render_markdown(pdf: _ReportPDF, text: str, font: str) -> None:
    lines = text.split("\n")
    in_code = False
    code_buf: list[str] = []

    for line in lines:
        if line.strip().startswith("```"):
            if not in_code:
                in_code = True
                code_buf = []
            else:
                in_code = False
                _render_code(pdf, code_buf)
                code_buf = []
            continue
        if in_code:
            code_buf.append(line)
            continue

        stripped = _strip_emoji(line)
        if font == "Helvetica":
            stripped = _sanitize_latin1(stripped)

        if line.startswith("### "):
            pdf.set_font(font, "B", 11)
            pdf.set_text_color(50, 50, 50)
            _safe_cell(pdf, 6, stripped[4:].strip())
            pdf.ln(1)
        elif line.startswith("## "):
            pdf.ln(2)
            pdf.set_font(font, "B", 12)
            pdf.set_text_color(30, 30, 30)
            _safe_cell(pdf, 7, stripped[3:].strip())
            pdf.ln(2)
        elif line.startswith("# "):
            pdf.ln(3)
            pdf.set_font(font, "B", 14)
            pdf.set_text_color(20, 20, 20)
            _safe_cell(pdf, 8, stripped[2:].strip())
            pdf.ln(3)
        elif re.match(r"^[-*] ", line):
            content = _inline(stripped[2:].strip())
            pdf.set_font(font, "", 10)
            pdf.set_text_color(40, 40, 40)
            _safe_cell(pdf, 6, f"  *  {content}")
        elif re.match(r"^\d+\. ", line):
            content = _inline(re.sub(r"^\d+\. ", "", stripped))
            pdf.set_font(font, "", 10)
            pdf.set_text_color(40, 40, 40)
            _safe_cell(pdf, 6, f"  {content}")
        elif line.strip() in ("---", "***", "___"):
            pdf.set_draw_color(210, 210, 210)
            pdf.set_line_width(0.2)
            y = pdf.get_y() + 2
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(5)
        elif line.strip() == "":
            pdf.ln(3)
        else:
            content = _inline(stripped)
            if not content:
                continue
            pdf.set_font(font, "", 10)
            pdf.set_text_color(40, 40, 40)
            _safe_cell(pdf, 6, content)

    if in_code and code_buf:
        _render_code(pdf, code_buf)


def _inline(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*",     r"\1", text)
    text = re.sub(r"`(.*?)`",       r"\1", text)
    return text.strip()


def _break_long_line(line: str, max_chars: int = 90) -> list[str]:
    """Split lines with no natural break points into chunks."""
    if len(line) <= max_chars or " " in line:
        return [line]
    return [line[i:i + max_chars] for i in range(0, len(line), max_chars)]


def _render_code(pdf: _ReportPDF, lines: list[str]) -> None:
    if not lines:
        return
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font("Courier", "", 8)
    pdf.set_text_color(60, 60, 60)
    for line in lines:
        line = _sanitize_latin1(_strip_emoji(line))
        for chunk in _break_long_line(line):
            pdf.set_x(pdf.l_margin)
            if not chunk.strip():
                pdf.ln(5)
            else:
                pdf.multi_cell(0, 5, chunk, fill=True)
    pdf.set_x(pdf.l_margin)
    pdf.ln(3)


def generate_report_pdf(
    report_md: str,
    image_paths: list[str],
    lang: str = "en_US",
) -> bytes:
    """
    Build a PDF from a Markdown report string and optional PNG image paths.
    Returns raw PDF bytes suitable for st.download_button.
    """
    pdf = _ReportPDF(lang=lang)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(left=18, top=18, right=18)
    pdf.add_page()

    font = "Helvetica"
    if _has_cjk(report_md):
        cjk = _find_cjk_font()
        if cjk:
            try:
                pdf.add_font("CJK", "", cjk, uni=True)
                pdf.add_font("CJK", "B", cjk, uni=True)
                font = "CJK"
            except Exception:
                pass
    pdf._body_font = font

    pdf.set_font(font, "B", 18)
    pdf.set_text_color(30, 30, 30)
    title = "Analysis Report" if lang == "en_US" else "分析报告"
    title_text = f"{APP_DISPLAY}  {title}"
    if font == "Helvetica":
        title_text = _sanitize_latin1(title_text)
    pdf.cell(0, 12, title_text, ln=True)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(0, 6, datetime.now().strftime("%Y-%m-%d  %H:%M"), ln=True)
    pdf.ln(4)

    pdf.set_draw_color(76, 139, 245)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    _render_markdown(pdf, report_md, font)

    valid_imgs = [p for p in (image_paths or []) if os.path.isfile(p)]
    if valid_imgs:
        pdf.add_page()
        pdf.set_font(font, "B", 13)
        pdf.set_text_color(30, 30, 30)
        section = "Analysis Charts" if lang == "en_US" else "分析图表"
        pdf.cell(0, 10, section, ln=True)
        pdf.ln(3)

        img_w = pdf.w - pdf.l_margin - pdf.r_margin
        for img_path in valid_imgs:
            if pdf.get_y() > pdf.h - pdf.b_margin - 60:
                pdf.add_page()
            pdf.image(img_path, x=pdf.l_margin, w=img_w)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(150, 150, 150)
            pdf.cell(0, 5, os.path.basename(img_path), ln=True, align="C")
            pdf.ln(4)

    return bytes(pdf.output())
