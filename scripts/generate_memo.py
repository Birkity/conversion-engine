"""
Generate memo.pdf from memo.md using fpdf2.

Reads memo.md from the project root and writes memo.pdf there.
Target: exactly 2 pages.

Typography settings (tuned for 2-page fit):
  BODY=8.1pt  LINE_H=4.0mm  PARA_GAP=4.0mm
  T_FONT=7.0pt  T_H=3.6mm  margins=16mm

Usage:
    python scripts/generate_memo.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
except ImportError:
    print("fpdf2 not installed — run: pip install fpdf2")
    sys.exit(1)


# ── Typography constants ──────────────────────────────────────────────────────
BODY   = 8.1    # body font size (pt)
LINE_H = 4.0    # body line height (mm)
PARA_G = 4.0    # paragraph gap (mm)
H1_SZ  = 11.0
H2_SZ  = 9.5
H3_SZ  = BODY
T_FONT = 7.0    # table font size
T_H    = 3.6    # table row height (mm)
MARGIN = 16     # left/right/top margin (mm)
SEP_H  = 1.5    # separator line height


_UNICODE_MAP = str.maketrans({
    "—": "--",   # em dash
    "–": "-",    # en dash
    "’": "'",    # right single quote
    "‘": "'",    # left single quote
    "“": '"',    # left double quote
    "”": '"',    # right double quote
    "→": "->",   # →
    "←": "<-",   # ←
    "≥": ">=",   # ≥
    "≤": "<=",   # ≤
    "τ": "tau",  # τ
    "²": "2",    # ² (superscript 2)
    "±": "+/-",  # ±
    "•": "*",    # •  (bullet — replaced separately)
    "×": "x",    # ×
    "…": "...",  # …
})


def _latin1(text: str) -> str:
    """Sanitize Unicode to latin-1-safe characters."""
    return text.translate(_UNICODE_MAP)


def _strip_inline(text: str) -> str:
    """Remove bold/italic markers for plain-text rendering, then sanitize."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*",     r"\1", text)
    text = re.sub(r"`(.+?)`",       r"\1", text)
    return _latin1(text)


def _is_bold_inline(text: str) -> bool:
    return bool(re.match(r"^\*\*.*\*\*$", text.strip()))


class MemoBuilder(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_auto_page_break(auto=False)
        self.add_page()

    def _w(self):
        return self.w - 2 * MARGIN

    def body(self, text: str, indent: float = 0.0):
        self.set_font("Helvetica", size=BODY)
        clean = _strip_inline(text)
        self.set_x(MARGIN + indent)
        self.multi_cell(self._w() - indent, LINE_H, clean, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def body_bold(self, text: str):
        self.set_font("Helvetica", style="B", size=BODY)
        clean = _strip_inline(text)
        self.set_x(MARGIN)
        self.multi_cell(self._w(), LINE_H, clean, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def h1(self, text: str):
        self.set_font("Helvetica", style="B", size=H1_SZ)
        self.set_x(MARGIN)
        self.multi_cell(self._w(), LINE_H + 1, _strip_inline(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1.0)

    def h2(self, text: str):
        self.set_font("Helvetica", style="B", size=H2_SZ)
        self.set_x(MARGIN)
        self.multi_cell(self._w(), LINE_H, _strip_inline(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(0.5)

    def h3(self, text: str):
        self.set_font("Helvetica", style="B", size=H3_SZ)
        self.set_x(MARGIN)
        self.multi_cell(self._w(), LINE_H, _strip_inline(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def sep(self):
        self.ln(SEP_H)
        self.set_draw_color(160, 160, 160)
        self.line(MARGIN, self.get_y(), self.w - MARGIN, self.get_y())
        self.ln(SEP_H)

    def para_gap(self):
        self.ln(PARA_G)

    def table_row(self, cells: list[str], col_widths: list[float], header: bool = False):
        style = "B" if header else ""
        self.set_font("Helvetica", style=style, size=T_FONT)
        x0 = self.get_x()
        for cell, w in zip(cells, col_widths):
            self.cell(w, T_H, _strip_inline(cell.strip()), border=1)
        self.ln(T_H)


def _parse_table(lines: list[str]) -> tuple[list[list[str]], list[float]]:
    """Parse consecutive | lines into rows, skipping the |---|...| separator."""
    rows = []
    for ln in lines:
        if re.match(r"^\|[-: |]+\|$", ln.strip()):
            continue
        cols = [c for c in ln.strip().split("|") if c != ""]
        if cols:
            rows.append(cols)
    if not rows:
        return [], []
    n_cols = max(len(r) for r in rows)
    w_total = 178 - 2 * MARGIN + 2 * MARGIN   # full usable width
    # recalc: use actual PDF width
    w_each = (210 - 2 * MARGIN) / n_cols
    col_widths = [w_each] * n_cols
    return rows, col_widths


def build(src: Path, dst: Path) -> None:
    text = src.read_text(encoding="utf-8")
    raw_lines = text.splitlines()

    pdf = MemoBuilder()
    # correct usable width for table
    usable_w = pdf.w - 2 * MARGIN

    i = 0
    page_break_done = False
    while i < len(raw_lines):
        line = raw_lines[i]

        # ── Page 2 trigger (fires exactly once, at the main Page 1→2 divider) ─
        if line.strip() == "---" and i > 0:
            if not page_break_done and pdf.get_y() > pdf.h * 0.35:
                pdf.add_page()
                page_break_done = True
                i += 1
                continue
            else:
                pdf.sep()
                i += 1
                continue

        # ── Headings ──────────────────────────────────────────────────────────
        if line.startswith("# "):
            pdf.h1(line[2:])
            i += 1
            continue
        if line.startswith("## "):
            pdf.h2(line[3:])
            i += 1
            continue
        if line.startswith("### "):
            pdf.h3(line[4:])
            i += 1
            continue

        # ── Separator ─────────────────────────────────────────────────────────
        if line.strip() == "---":
            pdf.sep()
            i += 1
            continue

        # ── Italic/meta header lines (e.g. *To: ...*) ─────────────────────────
        if line.startswith("*") and line.endswith("*") and not line.startswith("**"):
            pdf.set_font("Helvetica", style="I", size=BODY - 0.5)
            pdf.set_x(MARGIN)
            pdf.multi_cell(usable_w, LINE_H, _strip_inline(line), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            i += 1
            continue

        # ── Table block ───────────────────────────────────────────────────────
        if line.startswith("|"):
            # Collect all consecutive | lines
            table_lines = []
            while i < len(raw_lines) and raw_lines[i].startswith("|"):
                table_lines.append(raw_lines[i])
                i += 1
            rows, _ = _parse_table(table_lines)
            if rows:
                n_cols = max(len(r) for r in rows)
                col_w = usable_w / n_cols
                col_widths = [col_w] * n_cols
                for ri, row in enumerate(rows):
                    # Pad short rows
                    while len(row) < n_cols:
                        row.append("")
                    pdf.table_row(row, col_widths, header=(ri == 0))
                pdf.ln(1.0)
            continue

        # ── Blank line ────────────────────────────────────────────────────────
        if line.strip() == "":
            pdf.para_gap()
            i += 1
            continue

        # ── Bullet ────────────────────────────────────────────────────────────
        if line.startswith("- ") or line.startswith("* "):
            pdf.body("- " + line[2:], indent=3.0)
            i += 1
            continue

        # ── Bold paragraph heading (e.g. **Summary**) ─────────────────────────
        if _is_bold_inline(line):
            pdf.body_bold(line)
            i += 1
            continue

        # ── Normal body text ──────────────────────────────────────────────────
        pdf.body(line)
        i += 1

    pdf.output(str(dst))
    print(f"Generated {dst}  ({dst.stat().st_size:,} bytes,  {pdf.page} page(s))")


if __name__ == "__main__":
    src = ROOT / "memo.md"
    dst = ROOT / "memo.pdf"
    build(src, dst)
