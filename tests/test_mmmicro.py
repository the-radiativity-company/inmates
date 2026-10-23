"""The M&M Micro spider and normalizer, run against saved copies of a letter index and two details pages."""
from pathlib import Path

from scrapy.http import HtmlResponse

from inmates.loader import normalize
from inmates.scraper.spiders.mmmicro import MMMicroSpider


FIXTURES = Path(__file__).parent / 'fixtures' / 'mmmicro'
ROOT = 'http://jail.example.org'


def response(url, name):
    return HtmlResponse(url=url, body=(FIXTURES / name).read_bytes(), encoding='utf-8')


def crawl():
    spider = MMMicroSpider(domain=f'{ROOT}/', county='crawford')
    assert spider.start_urls[0] == f'{ROOT}/index.aspx?id=A'
    assert len(spider.start_urls) == 26
    requests = list(spider.parse(response(spider.start_urls[0], 'index.html')))
    records = []
    for request in requests:
        page = response(request.url, f"details-{request.cb_kwargs['id']}.html")
        records += list(request.callback(page, **request.cb_kwargs))
    return requests, records


def test_spider_follows_each_signed_details_link_and_reads_the_card_and_charges():
    requests, (jane, richard) = crawl()
    assert [r.url for r in requests] == [f'{ROOT}/details.aspx?id=124905&sig=AbC%2b1%3d', f'{ROOT}/details.aspx?id=124947&sig=XyZ%3d']
    assert jane == {
        'Id': '124905', 'Name': 'DOE, JANE Q', 'Age': '37', 'Class': 'DETAINED BY JUDGE', 'Race/Sex': 'W/F',
        'Visit': 'Call Facility For Time**', 'Intake Date': '08/19/2026 1:42 PM',
        'Charges': [{'TCA Description': 'CRIMINAL DAMAGE TO PROPERTY', 'Bond': '0', 'Court Date': '11/06/2026'},
                    {'TCA Description': 'STALKING CLASS 4 FELONY', 'Bond': '2,500', 'Court Date': '12/01/2026'}],
    }
    assert (richard['Name'], richard['Class']) == ('VAN DYKE, RICHARD', 'CONVICTED FELON')
    assert richard['Charges'] == [{'TCA Description': 'HOLD FOR IDOC', 'Bond': '0', 'Court Date': None}]


def test_normalizer_keys_on_id_and_reads_class_bond_and_court_date():
    _, records = crawl()
    jane, richard = (normalize('crawford', r, platform='mmmicro') for r in records)
    assert (jane.name, jane.county_person_key, jane.age, jane.sex, jane.race) == ('DOE, JANE Q', '124905', 37, 'F', 'W')
    booking, = jane.bookings
    assert (booking.booking_date, booking.next_court_date, booking.financial_hold) == ('2026-08-19 13:42:00', '2026-12-01 00:00:00', 2500.0)
    assert (booking.detention_status, booking.hold_type) == ('detained', None)
    assert [c.description for c in booking.charges] == ['CRIMINAL DAMAGE TO PROPERTY', 'STALKING CLASS 4 FELONY']

    booking, = richard.bookings
    assert (richard.sex, richard.race) == ('M', 'B')
    assert (booking.detention_status, booking.hold_type, booking.financial_hold, booking.next_court_date) == ('sentenced', 'doc', 0.0, None)
