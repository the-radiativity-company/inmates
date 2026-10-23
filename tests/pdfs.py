"""Builds small PDFs for the PDF spider tests, so no roster of real people is checked in."""
from typing import Iterable
from typing import Tuple


Text = Tuple[float, float, str]  # x from the left edge, y from the top, text; both in points


def pdf(pages: Iterable[Iterable[Text]], width: float = 612, height: float = 792) -> bytes:
    """a PDF with one Helvetica text run per (x, y, text) on each page, positioned like a report generator would"""
    pages = [list(page) for page in pages]
    objects = ['<< /Type /Catalog /Pages 2 0 R >>', None, '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    kids = []
    for texts in pages:
        runs = ''.join(f'BT /F1 9 Tf {x:.1f} {height - y - 7:.1f} Td ({escape(text)}) Tj ET\n' for x, y, text in texts)
        stream = f'<< /Length {len(runs.encode("latin-1"))} >>\nstream\n{runs}endstream'
        objects.append(stream)
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] /Resources << /Font << /F1 3 0 R >> >> /Contents {len(objects)} 0 R >>')
        kids.append(f'{len(objects)} 0 R')
    objects[1] = f'<< /Type /Pages /Kids [{" ".join(kids)}] /Count {len(kids)} >>'
    out = b'%PDF-1.4\n'
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f'{number} 0 obj\n{body}\nendobj\n'.encode('latin-1')
    xref = len(out)
    out += f'xref\n0 {len(objects) + 1}\n0000000000 65535 f \n'.encode('latin-1')
    out += ''.join(f'{offset:010d} 00000 n \n' for offset in offsets).encode('latin-1')
    out += f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode('latin-1')
    return out


def escape(text: str) -> str:
    return text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
