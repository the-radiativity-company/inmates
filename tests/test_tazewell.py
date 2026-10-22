"""The Tazewell spider and normalizer, run against a saved copy of the in-custody table."""
from pathlib import Path

from scrapy.http import HtmlResponse

from inmates.loader import normalize
from inmates.scraper.spiders.tazewell import TazewellSpider


PAGE = Path(__file__).parent / 'fixtures' / 'tazewell' / 'index.html'
URL = 'https://sheriff.example.gov/inmate-lookup-c/'


def records():
    spider = TazewellSpider(domain=URL, county='tazewell')
    assert spider.start_urls == [URL]
    return list(spider.parse(HtmlResponse(url=URL, body=PAGE.read_bytes(), encoding='utf-8')))


def test_spider_yields_one_record_per_table_row_keyed_by_header():
    jane, richard = records()
    assert jane == {'BookDate': '07-18-2024', 'BookTime': '17:53', 'DetaineeID': '463929', 'LastName': 'DOE', 'FirstName': 'JANE',
                    'MiddleInit': 'Q', 'Age': '37', 'Race': 'W', 'Sex': 'F', 'Charge': 'FIRST DEGREE MURDER', 'Agency': 'PEORIA POLICE DEPT'}
    assert (richard['MiddleInit'], richard['Charge']) == (None, 'IN-STATE WARRANT')


def test_normalizer_keys_on_detainee_id_and_joins_the_name_and_booking_time():
    jane, richard = (normalize('tazewell', r) for r in records())
    assert (jane.name, jane.county_person_key, jane.age, jane.sex, jane.race) == ('DOE, JANE Q', '463929', 37, 'F', 'W')
    booking, = jane.bookings
    assert (booking.booking_date, booking.arresting_agency, booking.financial_hold) == ('2024-07-18 17:53:00', 'PEORIA POLICE DEPT', None)
    assert (booking.detention_status, booking.hold_type) == ('detained', None)
    assert [c.description for c in booking.charges] == ['FIRST DEGREE MURDER']

    assert richard.name == 'ROE, RICHARD'
    assert (richard.bookings[0].detention_status, richard.bookings[0].hold_type) == ('hold', 'warrant')
