import re

from scrapy import Spider

from inmates.scraper.pdf import lines


DOCUMENT = re.compile(r'ShowDocument\?id=(\d+)')
NAME = re.compile(r"^[A-Z][A-Z'`.\- ]+,(\s*[A-Z].*)?$")  # a long last name is printed alone, its first name clipped
# left edges of the report's columns, in points
NAME_COLUMN, CHARGES, BOND, COURT_DATE, TIME, COURTROOM = 130, 250, 425, 495, 555, 595
HEADINGS = ('Population', 'Front Mugshot', 'Last, First Name', 'Charges', 'Bond', 'Court Date', 'Time', 'Courtroom')


class AdamsSpider(Spider):
    """
    Adams County's jail population, a PDF the sheriff's page links as
    "New Population.pdf" (https://www.adamscountyil.gov/government/departments/sheriff-jail/county-jail/jail-inmate-list).
    One row per person: mugshot, "LAST, FIRST" with an AC # beneath, a
    charges cell of "statute - description" entries separated by semicolons
    and wrapped over several lines, a bond amount when one is set, the next
    court date, time, and courtroom, with the arrest type (New Arrest,
    Warrant Arrest, Sentence, Court Order, IDOC Writ, ...) printed under the
    courtroom.

    The county's edge (Akamai) answers HTTP/1.1 clients and bare requests
    with 403, and a browser's request over HTTP/2 with the page, so this
    spider uses Scrapy's HTTP/2 download handler on top of the browser
    headers every spider sends. The document id is read from the page each
    time, in case the county re-uploads the file.
    """
    name = 'adams'
    custom_settings = {
        'DOWNLOAD_HANDLERS': {'https': 'scrapy.core.downloader.handlers.http2.H2DownloadHandler'},
    }

    def __init__(self, domain=None, county=None, **kwargs):
        super().__init__(**kwargs)
        self.county = county
        self.start_urls = [domain] if domain else []

    def parse(self, response):
        match = DOCUMENT.search(response.text)
        if match:
            yield response.follow(f'/Home/ShowDocument?id={match.group(1)}', callback=self.parse_pdf)
        else:
            self.logger.error('no ShowDocument link on %s', response.url)

    def parse_pdf(self, response):
        if not response.body.startswith(b'%PDF'):
            self.logger.error('%s did not answer with a PDF (%s, %d bytes)', response.url, response.headers.get('Content-Type'), len(response.body))
            return
        printed = next((l.text.replace('Printed on', '').strip() for l in lines(response.body) if l.text.startswith('Printed on')), None)
        for block in self.blocks(lines(response.body)):
            record = self.parse_block(block)
            record['Printed'] = printed
            yield record

    def blocks(self, found):
        """one list of lines per person: a name in the name column starts a block, which runs to the next name"""
        block = None
        for line in found:
            if NAME_COLUMN <= line.x0 < CHARGES and NAME.match(line.text):
                if block:
                    yield block
                block = [line]
            elif line.text in HEADINGS or line.text.startswith(('Page ', 'Total Records', 'Printed on')):
                continue  # each page repeats the column headings; a block can run across the break
            elif block is not None:
                block.append(line)
        if block:
            yield block

    def parse_block(self, block):
        head, *rest = block
        record = {'Name': head.text, 'AC #': None, 'Charges': None, 'Bond': None, 'Court Date': None, 'Time': None, 'Courtroom': None, 'Arrest Type': None}
        charges = []
        for line in rest:
            x, text = line.x0, line.text
            if NAME_COLUMN <= x < CHARGES:
                if text.isdigit():
                    record['AC #'] = text
            elif CHARGES <= x < BOND:
                charges.append(text)
            elif BOND <= x < COURT_DATE:
                record['Bond'] = text
            elif COURT_DATE <= x < TIME:
                record['Court Date'] = text
            elif TIME <= x < COURTROOM:
                record['Time'] = text
            elif x >= COURTROOM:
                if text.startswith('Court Room'):
                    record['Courtroom'] = text
                else:
                    record['Arrest Type'] = text
        record['Charges'] = ' '.join(charges) or None
        return record
