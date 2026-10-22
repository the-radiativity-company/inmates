import re

from parsel import SelectorList
from scrapy import Spider


DETAIL_ID = re.compile(r'/Inmate/Detail/(-?\d+)')


def text_of(selector) -> str | None:
    """all descendant text of the first matched element, whitespace collapsed, None when empty"""
    nodes = selector if isinstance(selector, SelectorList) else SelectorList([selector])
    if not nodes:
        return None
    return ' '.join(' '.join(nodes[0].css('::text').getall()).split()) or None


def field_list(items) -> dict:
    """<li><label>Key</label><span>Value</span></li> ... -> {'Key': 'Value'}"""
    return {text_of(item.css('label')): text_of(item.css('span')) for item in items}


def grid(table) -> list:
    """a NewWorld Grid table -> one dict per body row keyed by header text; the 'No data' row yields nothing"""
    headers = [text_of(th) for th in table.css('thead th')]
    rows = []
    for tr in table.css('tbody tr'):
        cells = tr.css('td')
        if len(cells) != len(headers):
            continue
        rows.append({header: text_of(td) for header, td in zip(headers, cells)})
    return rows


class NewWorldSpider(Spider):
    """
    Tyler Technologies' NewWorld InmateInquiry, the roster software shared by
    Macon, Kendall, Kankakee, and Will. `domain` is the inquiry root for a county,
    e.g. http://50.77.170.147/NewWorld.InmateInquiry/IL0580000; any query string
    is dropped and replaced with InCustody=True, without which the inquiry lists
    every booking the county has ever recorded.

    The index is paged (a.Next inside .Pager, a div on older installs and a
    nav on newer ones); each row links to a detail page holding demographics,
    every booking, its bonds, court dates, and charges. One record per person
    is emitted from the detail page, carrying the detail URL's id as
    'Detail Id' since not every county prints a Subject Number.
    """
    name = 'newworld'
    custom_settings = {
        'DOWNLOAD_DELAY': 0.25,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
    }

    def __init__(self, domain=None, county=None, **kwargs):
        super().__init__(**kwargs)
        self.county = county
        self.root = (domain or '').split('?')[0].rstrip('/')
        self.start_urls = [f'{self.root}?InCustody=True'] if self.root else []

    def parse(self, response):
        for href in response.css('#Inmate_Index td.Name a::attr(href)').getall():
            yield response.follow(href, callback=self.parse_detail)
        next_page = response.css('#Inmate_Index .Pager a.Next::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_detail(self, response):
        person = field_list(response.css('#DemographicInformation ul.FieldList > li'))
        match = DETAIL_ID.search(response.url)
        person['Detail Id'] = match.group(1) if match else None
        person['Bookings'] = [self.parse_booking(booking) for booking in response.css('#BookingHistory div.Booking')]
        yield person

    def parse_booking(self, booking) -> dict:
        data = {'Booking Number': text_of(booking.css('h3 span'))}
        data.update(field_list(booking.css('div.BookingData > ul.FieldList > li')))
        data['Bonds'] = grid(booking.css('div.BookingBonds table'))
        data['Court Dates'] = grid(booking.css('div.BookingCourtInfo table'))
        data['Charges'] = grid(booking.css('div.BookingCharges table'))
        return data
