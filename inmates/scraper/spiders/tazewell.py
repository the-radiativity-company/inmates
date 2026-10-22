from scrapy import Spider

from inmates.scraper.text import text_of


class TazewellSpider(Spider):
    """
    Tazewell County's in-custody list, a Ninja Tables table on the sheriff's
    WordPress site (https://sheriff.tazewell-il.gov/inmate-lookup-c/). The
    whole table is rendered into the page and only the paging is done in the
    browser, so one GET is the whole roster.

    One record per body row, keyed by the header cells: BookDate, BookTime,
    DetaineeID, LastName, FirstName, MiddleInit, Age, Race, Sex, Charge,
    Agency. A person appears once, with a single charge and no bond.
    """
    name = 'tazewell'

    def __init__(self, domain=None, county=None, **kwargs):
        super().__init__(**kwargs)
        self.county = county
        self.start_urls = [domain] if domain else []

    def parse(self, response):
        for table in response.css('table'):
            headers = [text_of(th) for th in table.css('thead th')]
            if 'DetaineeID' not in headers:
                continue
            for tr in table.css('tbody tr'):
                cells = [text_of(td) for td in tr.css('td')]
                if len(cells) == len(headers):
                    yield dict(zip(headers, cells))
