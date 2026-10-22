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
    assert reasons[0] == {'label': 'Warrant', 'kind': 'warrant', 'text': 'Original Charge warrant 25CF463 issued by Rock Island CO. IL, IL',
                          'docket': '25CF463', 'agency': 'Rock Island CO. IL, IL', 'arrest_date': '09/09/2026', 'bond': '10%, $40000.00'}
    assert zuercher_hold_reasons('') == []


def test_hold_reasons_across_sheriffs_label_styles():
    """each sheriff configures its own entry labels; the parser keys on content"""
    def one(text):
        reason, = zuercher_hold_reasons(text)
        return {k: reason.get(k) for k in ('kind', 'statute', 'text', 'docket', 'agency')}

    assert one('New Offense: Converted Statute - 625 ILCS 5/11-204.1(A)(3) ~ AGGRAVATED FLEEING OR ELUDING;') == \
        {'kind': 'charge', 'statute': '625 ILCS 5/11-204.1(A)(3)', 'text': 'AGGRAVATED FLEEING OR ELUDING', 'docket': None, 'agency': None}
    assert one('Charge/Arrest: 720-5/12-3.4 - Violation of Order of Protection (Attempt) - 2 Counts; Bond - Pre-Trial Hold;') == \
        {'kind': 'charge', 'statute': '720 ILCS 5/12-3.4', 'text': 'Violation of Order of Protection (Attempt) - 2 Counts', 'docket': None, 'agency': None}
    assert one('Warrant-McDonough: Unspecified warrant 25CF8 issued by KNOX COUNTY (Converted Statute - WARRANT ~ WARRANT - FOREIGN);')['docket'] == '25CF8'
    assert one('Out of County Warrant (IL): Failure to Appear warrant 25MT175B issued by Sangamon, IL; Arrest Date 10/20/2026;')['agency'] == 'Sangamon, IL'
    assert one('Warrant New Charge: New Charge warrant  (720 ILCS 5/8-4(a) - Attempt Murder - 2 Counts); Bond - No Bond;') == \
        {'kind': 'warrant', 'statute': '720 ILCS 5/8-4(a)', 'text': 'Attempt Murder - 2 Counts', 'docket': None, 'agency': None}
    assert one('Sentencing Order: Serving 14 days - Concurrent; Arrest Date 10/16/2026;')['kind'] == 'sentence'
    assert one('Additional Hold for Parole; Arrest Date 08/24/2026; Bond - No Bond;') == \
        {'kind': 'hold', 'statute': None, 'text': 'Additional Hold for Parole', 'docket': None, 'agency': None}


def test_normalizer_handles_sentences_parole_holds_and_date_dobs():
    base = {'name': 'DOE, JANE', 'sex': 'Female', 'race': 'White', 'arrest_date': '2026-10-16', 'release_date': '', 'cell_block': '', 'held_for_agency': 'Example County Sheriff'}
    sentenced = normalize('x', dict(base, dob=33, hold_reasons='Sentencing Order: Serving 14 days - Concurrent; Arrest Date 10/16/2026; Bond - No Bond;'), 'zuercher')
    assert (sentenced.age, sentenced.dob, sentenced.bookings[0].detention_status, sentenced.bookings[0].charges) == (33, None, 'sentenced', [])

    parole = normalize('x', dict(base, dob='1997-06-10', hold_reasons='Original Warrant: Unspecified warrant ; Arrest Date 08/24/2026;<br />Additional Hold for Parole; Arrest Date 08/24/2026; Bond - No Bond;'), 'zuercher')
    assert (parole.age, parole.dob) == (None, '1997-06-10')
    assert (parole.bookings[0].detention_status, parole.bookings[0].hold_type) == ('hold', 'doc')

    local = normalize('x', dict(base, dob=20, hold_reasons='Out of County Warrant (IL): Failure to Appear warrant 25MT175B issued by Sangamon, IL; Arrest Date 10/20/2026;'), 'zuercher')
    assert (local.bookings[0].detention_status, local.bookings[0].hold_type, local.bookings[0].charges[0].docket_number) == ('detained', None, '25MT175B')


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
