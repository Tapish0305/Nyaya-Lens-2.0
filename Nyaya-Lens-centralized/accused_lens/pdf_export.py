"""Generate professional PDF exports for Nyaya Lens incident summary and lawyer brief."""
import io
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib import colors


def _clean_markdown_text(text: str) -> list[tuple[str, str]]:
    """Parse simple markdown into (type, content) pairs."""
    items = []
    lines = text.split('\n')
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            items.append(('spacer', ''))
            continue
        if line.startswith('# '):
            items.append(('h1', line[2:].strip()))
        elif line.startswith('## '):
            items.append(('h2', line[3:].strip()))
        elif line.startswith('### '):
            items.append(('h3', line[4:].strip()))
        elif line.startswith('- ') or line.startswith('* '):
            items.append(('bullet', line[2:].strip()))
        elif re.match(r'^\d+\.\s', line):
            items.append(('bullet', line))
        else:
            items.append(('p', line))
    return items


def _format_inline_tags(text: str) -> str:
    """Escape XML characters and convert basic markdown inline tags to ReportLab tags."""
    safe = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # **bold**
    safe = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', safe)
    # *italic*
    safe = re.sub(r'\*(.+?)\*', r'<i>\1</i>', safe)
    # `code`
    safe = re.sub(r'`(.+?)`', r'<font face="Courier">\1</font>', safe)
    return safe


def export_markdown_to_pdf(title: str, subtitle: str, markdown_content: str) -> bytes:
    """Convert markdown document to a styled PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=44,
        rightMargin=44,
        topMargin=44,
        bottomMargin=44,
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1A365D'),
        spaceAfter=4,
    )
    sub_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#718096'),
        spaceAfter=8,
    )
    h1_style = ParagraphStyle(
        'SecH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=colors.HexColor('#1A365D'),
        spaceBefore=12,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        'SecH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#2B6CB0'),
        spaceBefore=10,
        spaceAfter=4,
    )
    h3_style = ParagraphStyle(
        'SecH3',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#2D3748'),
        spaceBefore=8,
        spaceAfter=3,
    )
    p_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#2D3748'),
        spaceAfter=4,
    )
    bullet_style = ParagraphStyle(
        'BulletItem',
        parent=p_style,
        leftIndent=16,
        firstLineIndent=-10,
        spaceAfter=3,
    )

    story = []
    story.append(Paragraph(_format_inline_tags(title), title_style))
    if subtitle:
        story.append(Paragraph(_format_inline_tags(subtitle), sub_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2B6CB0'), spaceAfter=12))

    parsed = _clean_markdown_text(markdown_content)
    for kind, text in parsed:
        if kind == 'spacer':
            story.append(Spacer(1, 5))
        elif kind == 'h1':
            story.append(Paragraph(_format_inline_tags(text), h1_style))
        elif kind == 'h2':
            story.append(Paragraph(_format_inline_tags(text), h2_style))
        elif kind == 'h3':
            story.append(Paragraph(_format_inline_tags(text), h3_style))
        elif kind == 'bullet':
            story.append(Paragraph(f"&bull;&nbsp; {_format_inline_tags(text)}", bullet_style))
        elif kind == 'p':
            story.append(Paragraph(_format_inline_tags(text), p_style))

    doc.build(story)
    return buf.getvalue()
