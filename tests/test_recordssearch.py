"""The Tyler Corrections Records Search platform spider and normalizer, run against saved API responses."""
import json

from pathlib import Path

from scrapy import Request
from scrapy.http import TextResponse

from inmates.loader import normalize
from inmates.scraper.spiders.recordssearch import RecordsSearchSpider


FIXTURES = Path(__file__).parent / 'fixtures' / 'recordssearch'
ROSTER = 'https://correctionsrecordssearch.com/examplecountyil'
API = 'https://api.correctionsrecordssearch.com'
INSTANCE = '01EXAMPLEINSTANCE0000000000'


def response_from(name: str, url: str) -> TextResponse:
    return TextResponse(url=url, body=(FIXTURES / name).read_bytes(), encoding='utf-8')


def test_spider_looks_up_the_alias_then_pages_the_inmates():
    spider = RecordsSearchSpider(domain=ROSTER, county='example')
    assert spider.start_urls == [f'{API}/instances/lookup?alias=examplecountyil']
    first, = spider.parse(response_from('lookup.json', spider.start_urls[0]))
    assert first.url == f'{API}/instances/{INSTANCE}/inmates?page-size=500&page-number=1&sort-by=arrestDate&sort=desc'

    out = list(spider.parse_page(response_from('page.json', first.url), instance_id=INSTANCE, page=1))
    assert [r['name']['fullName'] for r in out if isinstance(r, dict)] == ['DOE, JANE Q', 'ROE, RICHARD']
    assert not [o for o in out if isinstance(o, Request)]  # total 2, both seen


def test_spider_pages_until_the_total_is_reached():
    spider = RecordsSearchSpider(domain=ROSTER, county='example')
    spider.page_size = 2
    body = (FIXTURES / 'page.json').read_text().replace('"total":2', '"total":5').encode()
    response = TextResponse(url=f'{API}/instances/{INSTANCE}/inmates', body=body, encoding='utf-8')
    next_page, = [o for o in spider.parse_page(response, instance_id=INSTANCE, page=1) if isinstance(o, Request)]
    assert 'page-size=2&page-number=2' in next_page.url


def test_normalizer_flattens_arrests_into_charges_and_keys_on_so_number():
    jane, richard = json.loads((FIXTURES / 'page.json').read_text())['inmates']
    p = normalize('peoria', jane, 'recordssearch')
    assert (p.name, p.county_person_key, p.age, p.sex, p.race) == ('DOE, JANE Q', '00173446', 37, 'F', 'WHITE')
    booking, = p.bookings
    assert (booking.booking_date, booking.arresting_agency) == ('2026-10-22 14:30:00', 'City of Anytown Police Department')
    assert (booking.detention_status, booking.hold_type, booking.financial_hold) == ('detained', None, 5000)
    assert [(c.description, c.offense_class, c.docket_number, c.offense_date) for c in booking.charges] == [
        ('RETAIL THEFT', 'Class A Misdemeanor', None, '2026-09-01 08:00:00'),
        ('AGGRAVATED BATTERY', 'Class 3 Felony', '26CF100', '2026-10-22 14:30:00'),
        ('FAILURE TO APPEAR', 'Local Petty Offense (not from State)', None, '2026-10-22 14:30:00'),
    ]

    booking, = normalize('peoria', richard, 'recordssearch').bookings
    assert (booking.detention_status, booking.hold_type, booking.financial_hold) == ('hold', 'doc', None)

    released, = normalize('peoria', dict(jane, IsReleased=True), 'recordssearch').bookings
    assert released.detention_status == 'released'
