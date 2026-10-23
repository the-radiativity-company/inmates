import re
import string

from scrapy import Spider

from inmates.scraper.text import text_of


DETAIL = re.compile(r"popup\('(details\.aspx\?id=(\d+)[^']*)'\)")
COLUMNS = re.compile(r'\s{2,}')


def card_name(card) -> str:
    """the name is printed in fixed-width columns, LAST FIRST MIDDLE, two or more spaces apart"""
    last, *rest = COLUMNS.split((card.css('.inmateName a::text').get() or '').strip())
    return ', '.join(filter(None, (last, ' '.join(rest)))) or None


class MMMicroSpider(Spider):
    """
    M&M Micro Systems' Online Inmate System, used by Crawford
    (http://jail.crawfordcountyil.org/). `domain` is the site root. The
    index is split by first letter of the last name, index.aspx?id=A through
    Z, each listing a card per person: name, age, class, race/sex, intake
    date. The name opens a details page, reachable only with the signed
    `sig` the card carries, that repeats the card and adds a charges table
    (TCA Description, Bond, Court Date).

    One record per person is emitted from the details page: the card's
    fields, the numeric id from the details URL, and the charges. The name is
    printed in fixed-width columns (LAST, then FIRST, then MIDDLE) and is
    emitted as 'LAST, FIRST MIDDLE'.
    """
    name = 'mmmicro'
    custom_settings = {
        'DOWNLOAD_DELAY': 0.25,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
    }

    def __init__(self, domain=None, county=None, **kwargs):
        super().__init__(**kwargs)
        self.county = county
        self.root = (domain or '').split('?')[0].rstrip('/')
        self.start_urls = [f'{self.root}/index.aspx?id={letter}' for letter in string.ascii_uppercase] if self.root else []

    def parse(self, response):
        for card in response.css('table.inmateContainer'):
            match = DETAIL.search(card.css('.inmateName a::attr(onclick)').get() or '')
            if match:
                yield response.follow(match.group(1), callback=self.parse_detail, cb_kwargs={'id': match.group(2)})

    def parse_detail(self, response, id):
        card = response.css('table.inmateContainer')
        record = {'Id': id, 'Name': card_name(card)}
        for row in card.css('table.genText tr'):
            cells = [text_of(td) for td in row.css('td')]
            for label, value in zip(cells[::2], cells[1::2]):
                if label:
                    record[label.rstrip(': ')] = value
        headers = [text_of(td) for td in response.css('#Main_showCharge tr:first-child td')]
        record['Charges'] = [
            dict(zip(headers, (text_of(td) for td in tr.css('td'))))
            for tr in response.css('#Main_showCharge tr')[1:]
            if len(tr.css('td')) == len(headers)
        ]
        yield record
