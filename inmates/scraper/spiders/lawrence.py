from scrapy import Spider

from inmates.scraper.text import text_of


class LawrenceSpider(Spider):
    """
    Lawrence County's "Inmates Currently in Custody" page
    (https://www.lawrencecsd.com/LCIMTS.htm), a single static page from the
    sheriff's own system. Each person is an <article> with a mugshot, a name
    in <h1>, labelled fields (<h2>Age:</h2><data>43</data>, ...), and a
    table of charges with a bond figure for each.

    One record per article: Name, Age, Class, Race/Sex, Intake Date, City,
    Arrested By Department, Arrested By Officer, Release Date, and a Charges
    list of {Charge, Bond}. The base64 mugshot is left out.
    """
    name = 'lawrence'

    def __init__(self, domain=None, county=None, **kwargs):
        super().__init__(**kwargs)
        self.county = county
        self.start_urls = [domain] if domain else []

    def parse(self, response):
        for article in response.xpath('//main//article[.//h1]'):
            record = {'Name': text_of(article.css('h1'))}
            for label in article.css('section h2, section h3'):
                key = (text_of(label) or '').rstrip(':').strip()
                value = text_of(label.xpath('following-sibling::data[1]'))
                if key and record.get(key) is None:  # 'Class' is printed twice, usually empty
                    record[key] = value
            record['Charges'] = [
                {'Charge': text_of(cells[0]), 'Bond': text_of(cells[1])}
                for cells in (tr.css('td') for tr in article.css('table.charges tr'))
                if len(cells) == 2
            ]
            yield record
