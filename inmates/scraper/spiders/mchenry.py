import re

from scrapy import Spider

from inmates.scraper.pdf import lines
from inmates.scraper.pdf import rows


# left edges of the columns in the per-person charges table, in points
STATUS, CHARGE, CLASS, CASE, COURT_DATE, COURT_ROOM, RELEASE = 20, 110, 380, 410, 480, 590, 660
ANCHORS = ('Class', 'Next Court Date', 'Court Room', 'Sentenced Release Date')
FURNITURE = ('Last Updated', 'This report', 'incarcerated in this facility', '***All subjects', 'Although every effort', "McHenry County Sheriff's Office Correctional", 'Page ')
COLUMNS = (
    ('Status', STATUS, CHARGE),
    ('Charge', CHARGE, CLASS),
    ('Class', CLASS, CASE),
    ('Case #', CASE, COURT_DATE),
    ('Next Court Date', COURT_DATE, COURT_ROOM),
    ('Court Room', COURT_ROOM, RELEASE),
    ('Sentenced Release Date', RELEASE, 10_000),
)
NAME = re.compile(r"^[A-Z][A-Z'`.\- ]+,(\s*[A-Z].*)?$")
LABELS = ('Date Confined', 'Date of Birth', 'Age', 'Status', 'Charges', 'Class', 'Case #', 'Next Court Date', 'Court Room', 'Sentenced Release Date')


class McHenrySpider(Spider):
    """
    McHenry County's hourly in-custody report, a PDF of a hundred-odd pages
    (https://www.mchenrysheriff.org/wp-content/uploads/pdf-uploads/InmateSearch_ByName.pdf).
    Each person is a block: a name and JCA# at the left edge, with Date
    Confined, Date of Birth, and Age beside them; a custody line (CURRENTLY
    CONFINED, or RECENTLY RELEASED ON ... ); a bond line (No Bond At This
    Time, or Bond Is Set At $...); an optional "**SUBJECT MAY HAVE A HOLD FOR
    ANOTHER AGENCY**" flag; then a charges table whose columns are Status,
    Charges, Class, Case #, Next Court Date, Court Room, Sentenced Release
    Date. Long charge descriptions wrap onto lines holding nothing else, and
    a two-word status ("Remand for" / "Sentence") wraps the same way, as do
    long names. A block can run over a page break, which once in a while
    loses the name line, and the hold flag sits just above the name it
    belongs to. Federal detainees are left out.

    One record per block, with 'Charges' as a list of dicts keyed by column.
    """
    name = 'mchenry'

    def __init__(self, domain=None, county=None, **kwargs):
        super().__init__(**kwargs)
        self.county = county
        self.start_urls = [domain] if domain else []

    def parse(self, response):
        for block in self.blocks(lines(response.body)):
            yield self.parse_block(block)

    def blocks(self, found):
        """splits the report's lines into one list per person, each starting at a name; page furniture is dropped"""
        block = None
        pending = []  # a hold flag printed above the name it belongs to
        for line in found:
            text = line.text
            if text.startswith(FURNITURE) and (line.x0 < 220 or text.startswith('Last Updated')):
                continue
            if text.startswith('**SUBJECT'):
                pending.append(line)
                continue
            is_name = line.x0 < 35 and NAME.match(text) and not text.startswith(('CURRENTLY', 'RECENTLY'))
            orphan = text.startswith('JCA#') and block is not None and any(l.text.startswith('JCA#') for l in block)
            if is_name or orphan:
                carried = []
                if orphan:
                    # a second JCA# in one block: the name above it was lost to a page break, and the
                    # date and age lines printed just above the JCA# belong with it, not the block before
                    while block and block[-1].page == line.page and line.y - block[-1].y <= 16:
                        carried.insert(0, block.pop())
                if block:
                    yield block
                block = [*carried, line, *pending] if orphan else [line, *pending]
                pending = []
            elif block is not None:
                block.append(line)
        if block:
            yield block

    def parse_block(self, block):
        head, *rest = block
        if not NAME.match(head.text):
            head, rest = None, block
        record = {'Name': head.text if head else None, 'Charges': []}
        table = []
        in_table = False
        for line in rest:
            text = line.text
            if text.startswith('JCA#'):
                record['JCA#'] = text.split(':', 1)[1].strip()
            elif text.startswith('**SUBJECT') or text.endswith('AGENCY**'):
                record['Hold'] = ' '.join(filter(None, (record.get('Hold'), text.strip('*'))))
            elif text in LABELS:
                in_table = in_table or text == 'Status'
            elif in_table:
                table.append(line)
            else:
                self.parse_head(record, line)
        record['Charges'] = list(self.parse_table(table))
        return record

    def parse_head(self, record, line):
        """the lines between the name and the charges table: dates, age, custody, bond"""
        text = line.text
        if line.x0 < 35 and 'JCA#' not in record and text.isupper() and not text.startswith(('CURRENTLY', 'RECENTLY')):
            record['Name'] = ' '.join(filter(None, (record['Name'], text)))
        elif line.x0 < 35:
            record['Custody'] = ' '.join(filter(None, (record.get('Custody'), text)))
        elif text.startswith(('No Bond', 'Bond Is Set')):
            record['Bond'] = text
        elif 250 <= line.x0 < 380 and '@' in text:
            record['Date Confined'] = text
        elif 380 <= line.x0 < 480 and '/' in text:
            record['Date of Birth'] = text
        elif 480 <= line.x0 < 520 and text.isdigit():
            record['Age'] = text

    def parse_table(self, table):
        """
        one dict per charge row. A row of the table is a baseline; a baseline
        with a Class, Next Court Date, Court Room, or Sentenced Release Date
        cell starts a charge, and any other continues the charge above: a
        wrapped description or the second word of a two-line status is joined
        on, and anything else on such a line is kept under 'Notes'.
        """
        charges = []
        for row in rows(table):
            cells = {}
            for line in row:
                name = next((n for n, left, right in COLUMNS if left <= line.x0 < right), None)
                if name:
                    cells[name] = ' '.join(filter(None, (cells.get(name), line.text)))
            if not cells:
                continue
            if any(name in cells for name in ANCHORS) or not charges:
                charges.append(cells)
                continue
            for name, text in cells.items():
                if name in ('Status', 'Charge'):
                    charges[-1][name] = ' '.join(filter(None, (charges[-1].get(name), text)))
                else:
                    charges[-1].setdefault('Notes', []).append(text)
        return charges
