from scrapy import Spider

from inmates.scraper.text import text_of


class JasperSpider(Spider):
    """
    Jasper County's jail report, a hand-typed WordPress page
    (https://jaspercountyillinois.gov/sheriff-office-jail/jail-report/).
    Inside the report section a bold paragraph names a person and the
    paragraphs after it read "Charge: ..." and "Bond: ...", one block per
    person, with blank paragraphs between.

    One record per bold name, carrying whatever labelled lines follow it
    until the next name.
    """
    name = 'jasper'

    def __init__(self, domain=None, county=None, **kwargs):
        super().__init__(**kwargs)
        self.county = county
        self.start_urls = [domain] if domain else []

    def parse(self, response):
        record = None
        for paragraph in response.css('.welcome-section p'):
            text = text_of(paragraph)
            if not text:
                continue
            label, colon, value = text.partition(':')
            if colon and len(label) <= 30 and record is not None:
                record[label.strip()] = value.strip() or None
            elif paragraph.css('strong'):
                if record:
                    yield record
                record = {'Name': text}
        if record:
            yield record
