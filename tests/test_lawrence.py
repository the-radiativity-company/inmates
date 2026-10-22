"""The Lawrence spider and normalizer, run against a saved copy of the in-custody page."""
from pathlib import Path

from scrapy.http import HtmlResponse

from inmates.loader import normalize
from inmates.scraper.spiders.lawrence import LawrenceSpider


PAGE = Path(__file__).parent / 'fixtures' / 'lawrence' / 'page.html'
URL = 'https://www.example.com/LCIMTS.htm'


def records():
    spider = LawrenceSpider(domain=URL, county='lawrence')
    assert spider.start_urls == [URL]
    return list(spider.parse(HtmlResponse(url=URL, body=PAGE.read_bytes(), encoding='utf-8')))


def test_spider_yields_one_record_per_person_and_skips_the_site_heading():
    jane, richard = records()
    assert jane == {
        'Name': 'DOE, JANE Q', 'Age': '37', 'Class': None, 'Race/Sex': 'W/F', 'Intake Date': '05/13/2026 11:54 PM',
        'City': 'BRIDGEPORT', 'Arrested By Department': 'BRIDGEPORT POLICE', 'Arrested By Officer': 'BPD', 'Release Date': None,
        'Charges': [{'Charge': 'U/L POSS. OF A WEAPON BY FELON', 'Bond': '0'}, {'Charge': 'POSSESSION OF METHAMPHETAMINE', 'Bond': '5000'}],
    }
    assert (richard['Name'], richard['Class'], richard['Charges']) == ('ROE, RICHARD', 'M', [{'Charge': 'TIME SERVER', 'Bond': '0'}])
    assert not any('img' in key.lower() or 'mugshot' in key.lower() for key in jane)


def test_normalizer_splits_race_sex_and_takes_the_largest_bond():
    jane, richard = (normalize('lawrence', r) for r in records())
    assert (jane.name, jane.county_person_key, jane.age, jane.sex, jane.race) == ('DOE, JANE Q', 'doe, jane q|2026-05-13', 37, 'F', 'W')
    booking, = jane.bookings
    assert (booking.booking_date, booking.release_date, booking.arresting_agency) == ('2026-05-13 23:54:00', None, 'BRIDGEPORT POLICE')
    assert (booking.detention_status, booking.hold_type, booking.financial_hold) == ('detained', None, 5000.0)
    assert [c.description for c in booking.charges] == ['U/L POSS. OF A WEAPON BY FELON', 'POSSESSION OF METHAMPHETAMINE']

    booking, = richard.bookings
    assert (booking.detention_status, booking.hold_type, booking.financial_hold) == ('sentenced', None, 0.0)


def test_normalizer_reads_holds_and_releases():
    jane, _ = records()
    doc = normalize('lawrence', dict(jane, Charges=[{'Charge': 'ILLINOIS DEPT OF CORRECTIONS', 'Bond': '0'}]))
    assert (doc.bookings[0].detention_status, doc.bookings[0].hold_type) == ('hold', 'doc')
    released = normalize('lawrence', dict(jane, **{'Release Date': '10/20/2026 09:00 AM'}))
    assert (released.bookings[0].detention_status, released.bookings[0].release_date) == ('released', '2026-10-20 09:00:00')
