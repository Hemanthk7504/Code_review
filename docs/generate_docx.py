"""Generate professional, executive-styled DOCX from COMPLETE_WORKING_DOCUMENT.md."""
import os
import re
import shutil
from pathlib import Path

import docx
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor


def set_cell_shading(cell, color_hex):
    """Set cell background color."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    tc_pr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set inner cell padding."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tc_pr.append(tc_mar)


def add_code_block(doc, code_text):
    """Add a shaded monospace code block."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    cell = table.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_shading(cell, "F4F5F7")
    set_cell_margins(cell, top=120, bottom=120, left=180, right=180)

    # Cell border (left accent line)
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="D0D5DD"/>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="1B365D"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="D0D5DD"/>'
        f'<w:right w:val="single" w:sz="4" w:space="0" w:color="D0D5DD"/>'
        f'</w:tcBorders>'
    )
    tc_pr.append(borders)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15

    for i, line in enumerate(code_text.splitlines()):
        if i > 0:
            p = cell.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
        run = p.add_run(line if line else " ")
        run.font.name = "Consolas"
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(33, 37, 41)


def add_callout(doc, text):
    """Add a quote / callout box."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    cell = table.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_shading(cell, "EBF3FA")
    set_cell_margins(cell, top=140, bottom=140, left=200, right=180)

    tc_pr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="single" w:sz="32" w:space="0" w:color="0284C7"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tc_pr.append(borders)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(10.5)
    run.font.italic = True
    run.font.color.rgb = RGBColor(15, 23, 42)


def format_runs(p, text):
    """Format inline markdown bold, italics, code backticks."""
    # Pattern matching bold (`**text**`), code (`code`), math (`$math$`)
    tokens = re.split(r'(\*\*.*?\*\*|`.*?`|\$.*?\$)', text)
    for token in tokens:
        if not token:
            continue
        if token.startswith("**") and token.endswith("**"):
            run = p.add_run(token[2:-2])
            run.bold = True
        elif token.startswith("`") and token.endswith("`"):
            run = p.add_run(token[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(194, 24, 91)
        elif token.startswith("$") and token.endswith("$"):
            run = p.add_run(token[1:-1])
            run.font.italic = True
            run.font.color.rgb = RGBColor(27, 54, 93)
        else:
            p.add_run(token)


def main():
    md_path = Path("docs/COMPLETE_WORKING_DOCUMENT.md")
    if not md_path.exists():
        print("Error: docs/COMPLETE_WORKING_DOCUMENT.md not found")
        return

    content = md_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    doc = Document()

    # Page Margins: 1 inch all sides
    for s in doc.sections:
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)

    # Base Normal Style
    style_normal = doc.styles["Normal"]
    style_normal.font.name = "Calibri"
    style_normal.font.size = Pt(11)
    style_normal.font.color.rgb = RGBColor(33, 37, 41)

    # Document Header Title
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(12)
    title_p.paragraph_format.space_after = Pt(4)
    run_title = title_p.add_run("CodeSentinel v2.0")
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(26)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(27, 54, 93)  # Deep Navy

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_before = Pt(0)
    sub_p.paragraph_format.space_after = Pt(18)
    run_sub = sub_p.add_run("Complete Architectural Specification & Operational Working Manual")
    run_sub.font.name = "Calibri"
    run_sub.font.size = Pt(14)
    run_sub.font.italic = True
    run_sub.font.color.rgb = RGBColor(74, 85, 104)

    # Metadata banner
    meta_p = doc.add_paragraph()
    meta_p.paragraph_format.space_before = Pt(0)
    meta_p.paragraph_format.space_after = Pt(24)
    meta_run = meta_p.add_run("Autonomous Multi-Agent AI Code Review · Risk-Adaptive Verification · Closed-Loop PR Automation\nTarget: Production & Enterprise CI/CD Deployment")
    meta_run.font.size = Pt(10)
    meta_run.font.color.rgb = RGBColor(100, 116, 139)

    i = 0
    in_code_block = False
    code_lines = []

    while i < len(lines):
        line = lines[i]

        # Handle Code block fences (``` or ````)
        if line.strip().startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lines = []
            else:
                in_code_block = False
                add_code_block(doc, "\n".join(code_lines))
                p_spacer = doc.add_paragraph()
                p_spacer.paragraph_format.space_before = Pt(0)
                p_spacer.paragraph_format.space_after = Pt(4)
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            i += 1
            continue

        # Skip horizontal rules
        if stripped in {"---", "***", "___"}:
            i += 1
            continue

        # Skip markdown title if already rendered
        if stripped.startswith("# 🛡️ CodeSentinel"):
            i += 1
            continue

        # Blockquote >
        if stripped.startswith(">"):
            quote_text = stripped.lstrip("> ").strip()
            add_callout(doc, quote_text)
            p_spacer = doc.add_paragraph()
            p_spacer.paragraph_format.space_before = Pt(0)
            p_spacer.paragraph_format.space_after = Pt(4)
            i += 1
            continue

        # Heading 1: ##
        if stripped.startswith("## "):
            h_text = stripped[3:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(18)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(h_text)
            run.font.name = "Calibri"
            run.font.size = Pt(18)
            run.font.bold = True
            run.font.color.rgb = RGBColor(27, 54, 93)  # Navy
            i += 1
            continue

        # Heading 2: ###
        if stripped.startswith("### "):
            h_text = stripped[4:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(h_text)
            run.font.name = "Calibri"
            run.font.size = Pt(14)
            run.font.bold = True
            run.font.color.rgb = RGBColor(3, 105, 161)  # Blue
            i += 1
            continue

        # Heading 3: ####
        if stripped.startswith("#### "):
            h_text = stripped[5:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(h_text)
            run.font.name = "Calibri"
            run.font.size = Pt(12)
            run.font.bold = True
            run.font.color.rgb = RGBColor(51, 65, 85)
            i += 1
            continue

        # Table detection
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                table_lines.append(lines[i].strip())
                i += 1

            if len(table_lines) >= 2:
                # Parse markdown table
                rows = []
                for t_line in table_lines:
                    # Ignore separator rows |---|---|
                    if re.match(r'^\|[\s\-:|]+\|$', t_line):
                        continue
                    cells = [c.strip() for c in t_line.split("|")[1:-1]]
                    rows.append(cells)

                if rows:
                    col_count = max(len(r) for r in rows)
                    doc_table = doc.add_table(rows=len(rows), cols=col_count)
                    doc_table.alignment = WD_TABLE_ALIGNMENT.CENTER
                    doc_table.autofit = True

                    for r_idx, row_data in enumerate(rows):
                        for c_idx in range(col_count):
                            val = row_data[c_idx] if c_idx < len(row_data) else ""
                            cell = doc_table.cell(r_idx, c_idx)
                            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

                            # Header row formatting
                            if r_idx == 0:
                                set_cell_shading(cell, "1B365D")  # Dark Navy
                                set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
                                p = cell.paragraphs[0]
                                p.paragraph_format.space_before = Pt(2)
                                p.paragraph_format.space_after = Pt(2)
                                run = p.add_run(val)
                                run.font.name = "Calibri"
                                run.font.size = Pt(10)
                                run.font.bold = True
                                run.font.color.rgb = RGBColor(255, 255, 255)
                            else:
                                bg = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
                                set_cell_shading(cell, bg)
                                set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
                                p = cell.paragraphs[0]
                                p.paragraph_format.space_before = Pt(2)
                                p.paragraph_format.space_after = Pt(2)
                                format_runs(p, val)
                                for run in p.runs:
                                    if not run.font.name or run.font.name == "Calibri":
                                        run.font.size = Pt(9.5)

                    p_spacer = doc.add_paragraph()
                    p_spacer.paragraph_format.space_before = Pt(0)
                    p_spacer.paragraph_format.space_after = Pt(6)
            continue

        # Bullet List: - or *
        if stripped.startswith("- ") or stripped.startswith("* "):
            bullet_text = stripped[2:].strip()
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            format_runs(p, bullet_text)
            i += 1
            continue

        # Numbered List: 1.
        if re.match(r'^\d+\.\s', stripped):
            num_text = re.sub(r'^\d+\.\s', '', stripped).strip()
            p = doc.add_paragraph(style="List Number")
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            format_runs(p, num_text)
            i += 1
            continue

        # Standard Paragraph
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.line_spacing = 1.15
        format_runs(p, stripped)
        i += 1

    # Save destination 1: docs/ directory in repository
    out_repo = Path("docs/CodeSentinel_Complete_Working_Document.docx")
    doc.save(str(out_repo))
    print(f"Successfully generated DOCX at {out_repo.resolve()}")

    # Save destination 2: artifact directory
    artifact_dir = Path(r"C:\Users\heman\.gemini\antigravity\brain\cb798d56-354a-473e-a10a-e509fe706e1f")
    if artifact_dir.exists():
        out_artifact = artifact_dir / "CodeSentinel_Complete_Working_Document.docx"
        shutil.copyfile(str(out_repo), str(out_artifact))
        print(f"Successfully copied DOCX to artifact directory at {out_artifact}")


if __name__ == "__main__":
    main()
