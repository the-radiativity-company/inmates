import re

from scrapy import Spider

from inmates.scraper.text import text_of


class RandolphSpider(Spider):
    """
    Randolph County's inmate listing, a Southern Software page the sheriff's
    site shows in an iframe (https://swssite.net/DesktopInmates.htm). One
    static page, regenerated on the hour, holds everyone in custody.

    The first table carries the title and an "Updated" stamp. Every table
    after it is one person: a bold name in the first row, a Charges/Bond
    header row, one row per charge, then blank padding rows. Bond is text
    ("Must see Judge", "Held without Bond", "Hold Per S/A") or a dollar
    amount.
    """
    name = 'randolph'

    def __init__(self, domain=None, county=None, **kwargs):
        super().__init__(**kwargs)
        self.county = county
        self.start_urls = [domain] if domain else []

    def parse(self, response):
        tables = response.css('table')
        stamp = text_of(tables[0].xpath('.//tr[2]')) if tables else None
        updated = re.sub(r'^Updated\s*', '', stamp or '') or None
        for table in tables[1:]:
            name = text_of(table.xpath('.//tr[1]//b'))
            if not name:
                continue
            rows = ([text_of(td) for td in tr.css('td')] for tr in table.css('tr')[1:])
            charges = [{'Charge': cells[0], 'Bond': cells[1]}
                       for cells in rows if len(cells) >= 2 and cells[0] and cells[0] != 'Charges']
            yield {'Name': name, 'Charges': charges, 'Updated': updated}
