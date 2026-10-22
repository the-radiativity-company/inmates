"""The Zuercher platform spider and normalizer, run against a saved API page."""
import json

from pathlib import Path

from scrapy import Request
from scrapy.http import TextResponse

from inmates.loader import normalize
from inmates.loader.normalize import zuercher_hold_reasons
from inmates.scraper.spiders.zuercher import ZuercherSpider


PAGE = Path(__file__).parent / 'fixtures' / 'zuercher' / 'page.json'
PORTAL = 'https://example-911-il.zuercherportal.com/#/inmates'
API = 'https://example-911-il.zuercherportal.com/api/portal/inmates/load'


def test_spider_posts_to_the_api_and_drops_mugshots():
    spider = ZuercherSpider(domain=PORTAL, county='example')
    first, = spider.start_requests()
    assert (first.url, first.method) == (API, 'POST')
    assert json.loads(first.body)['paging'] == {'count': 100, 'start': 0}

    response = TextResponse(url=API, body=PAGE.read_bytes(), encoding='utf-8')
    out = list(spider.parse(response, start=0))
    records = [o for o in out if isinstance(o, dict)]
    assert [r['name'] for r in records] == ['DOE, JANE', 'ROE, RICHARD']
    assert 'mugshot' not in records[0]
    assert not [o for o in out if isinstance(o, Request)]  # both of the 2 seen: the API is done


def test_spider_pages_until_the_total_is_reached():
    spider = ZuercherSpider(domain=PORTAL, county='example')
    spider.page_size = 2
    body = PAGE.read_text().replace('"total_record_count": 2', '"total_record_count": 5').encode()
    response = TextResponse(url=API, body=body, encoding='utf-8')
    next_page, = [o for o in spider.parse(response, start=0) if isinstance(o, Request)]
    assert json.loads(next_page.body)['paging'] == {'count': 2, 'start': 2}


def test_hold_reasons_split_into_charges_and_warrants():
    reasons = zuercher_hold_reasons(json.loads(PAGE.read_text())['records'][1]['hold_reasons'])
    assert [r['kind'] for r in reasons] == ['warrant', 'warrant']
    assert reasons[0] == {'kind': 'warrant', 'text': 'Original Charge warrant', 'docket': '25CF463',
                          'agency': 'Rock Island CO. IL, IL', 'arrest_date': '09/09/2026', 'bond': '10%, $40000.00'}
    assert zuercher_hold_reasons('') == []


def test_zuercher_normalizer():
    jane, richard = json.loads(PAGE.read_text())['records']
    p = normalize('rockisland', jane, 'zuercher')
    assert (p.name, p.age, p.sex, p.race, p.facility) == ('DOE, JANE', 37, 'F', 'WHITE', 'B')
    assert p.county_person_key == 'doe, jane|2026-10-13'
    booking, = p.bookings
    assert (booking.booking_date, booking.detention_status, booking.hold_type, booking.financial_hold) == ('2026-10-13', 'detained', None, 0.0)
    charge, = booking.charges
    assert (charge.statute, charge.description, charge.offense_date) == ('720 ILCS 5/12-3.2', 'DOMESTIC BATTERY', '2026-10-13')

    booking, = normalize('rockisland', richard, 'zuercher').bookings
    assert (booking.detention_status, booking.hold_type, booking.financial_hold) == ('hold', 'out_of_state', 40000.0)
    assert [c.docket_number for c in booking.charges] == ['25CF463', 'FECR449520']

    local_warrant = dict(richard, hold_reasons='Warrant: Failure to Appear warrant 22MT791 issued by Rock Island CO. IL, IL; Arrest Date 10/21/2026; Bond - No Bond, $0.00;')
    booking, = normalize('rockisland', local_warrant, 'zuercher').bookings
    assert (booking.detention_status, booking.hold_type) == ('detained', None)
