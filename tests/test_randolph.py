"""The Randolph spider and normalizer, run against a saved copy of the Southern Software listing."""
from pathlib import Path

from scrapy.http import HtmlResponse

from inmates.loader import normalize
from inmates.scraper.spiders.randolph import RandolphSpider


PAGE = Path(__file__).parent / 'fixtures' / 'randolph' / 'DesktopInmates.htm'
URL = 'https://swssite.example.net/DesktopInmates.htm'


def records():
    spider = RandolphSpider(domain=URL, county='randolph')
    assert spider.start_urls == [URL]
    return list(spider.parse(HtmlResponse(url=URL, body=PAGE.read_bytes(), encoding='utf-8')))


def test_spider_yields_one_record_per_person_table_with_its_charges():
    jane, richard = records()
    assert jane == {
        'Name': 'Doe,Jane Q.',
        'Charges': [{'Charge': 'AGG BATTERY/USE DEADLY WEAPON', 'Bond': 'Hold Per S/A'},
                    {'Charge': 'SPEEDING 30-39 MPH OVER LIMIT', 'Bond': '$1,500.00'}],
        'Updated': '10/22/2026 09:06 PM',
    }
    assert richard['Charges'] == [{'Charge': 'IDOC WARRANT', 'Bond': 'Held without Bond'}]


def test_normalizer_spaces_the_name_and_takes_the_largest_dollar_bond():
    jane, richard = (normalize('randolph', r) for r in records())
    assert (jane.name, jane.county_person_key, jane.age) == ('Doe, Jane Q.', 'doe, jane q.', None)
    booking, = jane.bookings
    assert (booking.booking_date, booking.financial_hold, booking.detention_status, booking.hold_type) == (None, 1500.0, 'detained', None)
    assert [c.description for c in booking.charges] == ['AGG BATTERY/USE DEADLY WEAPON', 'SPEEDING 30-39 MPH OVER LIMIT']

    assert richard.name == 'Roe, Richard'
    assert (richard.bookings[0].financial_hold, richard.bookings[0].detention_status, richard.bookings[0].hold_type) == (0.0, 'hold', 'doc')
