"""The Jasper spider and normalizer, run against a saved copy of the hand-typed jail report."""
from pathlib import Path

from scrapy.http import HtmlResponse

from inmates.loader import normalize
from inmates.scraper.spiders.jasper import JasperSpider


PAGE = Path(__file__).parent / 'fixtures' / 'jasper' / 'jail-report.html'
URL = 'https://sheriff.example.gov/sheriff-office-jail/jail-report/'


def records():
    spider = JasperSpider(domain=URL, county='jasper')
    assert spider.start_urls == [URL]
    return list(spider.parse(HtmlResponse(url=URL, body=PAGE.read_bytes(), encoding='utf-8')))


def test_spider_yields_one_record_per_bold_name_with_the_labelled_lines_after_it():
    jane, richard, pat = records()
    assert jane == {
        'Name': 'Jane Q Doe',
        'Charge': 'Jasper County FTA Warrant-Aggravated methamphetamine Manuf/Apt/<15 Grams, Possession of methamphetamine 100-400 grams Intent to Deliver.',
        'Bond': 'No Bond',
    }
    assert richard == {'Name': 'Richard Roe', 'Charge': 'Mittimus.', 'Bond': '$1,500.00'}
    assert pat == {'Name': 'Pat Poe', 'Charge': 'Possession of methamphetamine, Violation of order of protection.'}


def test_normalizer_splits_charges_on_commas_and_reads_no_bond_as_zero():
    jane, richard, pat = (normalize('jasper', r) for r in records())
    assert (jane.name, jane.county_person_key) == ('Jane Q Doe', 'jane q doe')
    booking, = jane.bookings
    assert [c.description for c in booking.charges] == [
        'Jasper County FTA Warrant-Aggravated methamphetamine Manuf/Apt/<15 Grams',
        'Possession of methamphetamine 100-400 grams Intent to Deliver',
    ]
    assert (booking.financial_hold, booking.detention_status, booking.hold_type) == (0.0, 'hold', 'warrant')

    booking, = richard.bookings
    assert (booking.financial_hold, booking.detention_status, booking.hold_type) == (1500.0, 'sentenced', None)

    booking, = pat.bookings
    assert (booking.financial_hold, booking.detention_status, len(booking.charges)) == (None, 'detained', 2)
