"""Reading rosters published as PDFs: text lines with their position on the page."""
from dataclasses import dataclass
from io import BytesIO
from typing import Iterator
from typing import List

from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams
from pdfminer.layout import LTTextContainer
from pdfminer.layout import LTTextLine


@dataclass(frozen=True)
class Line:
    """one line of text and where it sits: y grows downward from the top of the page, x rightward"""
    page: int
    y: int
    x0: int
    x1: int
    text: str

    def within(self, left: float, right: float) -> bool:
        """whether the line starts inside a column band"""
        return left <= self.x0 < right


def lines(body: bytes, char_margin: float = 1.0) -> List[Line]:
    """
    every non-blank text line in the PDF, in reading order (page, then top to
    bottom, then left to right). char_margin is pdfminer's threshold for
    joining neighbouring characters into one line, in character widths; the
    default of 1.0 keeps words together but splits adjacent table cells.
    """
    found = []
    params = LAParams(char_margin=char_margin)
    for number, page in enumerate(extract_pages(BytesIO(body), laparams=params), start=1):
        for box in page:
            if not isinstance(box, LTTextContainer):
                continue
            for line in box:
                if isinstance(line, LTTextLine):
                    text = ' '.join(line.get_text().split())
                    if text:
                        found.append(Line(number, round(page.height - line.y1), round(line.x0), round(line.x1), text))
    found.sort(key=lambda l: (l.page, l.y, l.x0))
    return found


def rows(found: List[Line], tolerance: int = 3) -> Iterator[List[Line]]:
    """groups lines on the same page that share a baseline, within `tolerance` points, into rows"""
    row: List[Line] = []
    for line in found:
        if row and (line.page != row[0].page or abs(line.y - row[0].y) > tolerance):
            yield row
            row = []
        row.append(line)
    if row:
        yield row
