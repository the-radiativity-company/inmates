import re

from scrapy import Spider

from inmates.scraper.pdf import lines
from inmates.scraper.pdf import rows


class LeeSpider(Spider):
    """
    Lee County's "Current Inmate List, by Name", a PDF the county posts in
    its document center (https://www.leecountyil.com/DocumentCenter/View/2814).
    Two columns, Name and Booking #, across as many pages as it takes, with a
    report date stamped on each page and a "Total Housed Inmates" line at the
    end. Nothing else: no charges, bond, or dates.

    One record per row that pairs a name with a booking number.
    """
    name = 'lee'
    booking_number = re.compile(r'^\d{2}LJ-\d{4}$')

    def __init__(self, domain=None, county=None, **kwargs):
        super().__init__(**kwargs)
        self.county = county
        self.start_urls = [domain] if domain else []

    def parse(self, response):
        found = lines(response.body)
        stamp = next((l.text for l in found if re.fullmatch(r'\d{2}/\d{2}/\d{2,4}', l.text)), None)
        for row in rows(found):
            if len(row) == 2 and self.booking_number.match(row[1].text):
                yield {'Name': row[0].text, 'Booking #': row[1].text, 'Report Date': stamp}
