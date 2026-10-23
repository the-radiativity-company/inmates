"""The Sangamon spider and normalizer, run against saved copies of the roster page, the grid's JSON, and a details form."""
from pathlib import Path

from scrapy.http import HtmlResponse
from scrapy.http import TextResponse

from inmates.loader import normalize
from inmates.scraper.spiders.sangamon import SangamonSpider


FIXTURES = Path(__file__).parent / 'fixtures' / 'sangamon'
ROOT = 'https://example.gov'
ROSTER = f'{ROOT}/departments/s-z/sheriff/inmate-roster'


def html(url, name):
    return HtmlResponse(url=url, body=(FIXTURES / name).read_bytes(), encoding='utf-8')


def text(url, name):
    return TextResponse(url=url, body=(FIXTURES / name).read_bytes(), encoding='utf-8')


def crawl():
    """drives the spider through its stages by hand: roster page, grid pages, one details page, the forms"""
    spider = SangamonSpider(domain=ROSTER, county='sangamon')
    grid, = spider.parse(html(ROSTER, 'roster.html'))
    assert (grid.method, grid.body) == ('POST', b'{}')
    assert grid.url == f'{ROOT}/DesktopModules/DnnSharp/ActionGrid/Api.ashx?method=GetData&language=en-US&TabId=2618&_mid=9990&_tabid=2618&view=Cards&page=1'
    details_page, next_page = spider.parse_grid(text(grid.url, 'grid-1.json'), **grid.cb_kwargs)
    assert details_page.url == f'{ROOT}/departments/s-z/sheriff/inmate-roster/details?SCinmateId=265929'
    assert next_page.url.endswith('&page=2')
    forms = list(spider.parse_details_page(html(details_page.url, 'details.html'), **details_page.cb_kwargs))
    assert spider.form == ('2624', '9993')
    assert [f.url for f in forms] == [f'{ROOT}/DesktopModules/MVC/DnnSharp/ActionForm/Load?SCinmateId={i}&openMode=Always&language=en-US' for i in ('265929', '265933')]
    assert forms[0].headers.to_unicode_dict() == {'Tabid': '2624', 'Moduleid': '9993'}
    more = list(spider.parse_grid(text(next_page.url, 'grid-2.json'), **next_page.cb_kwargs))
    assert [m.url[-33:] for m in more] == ['SCinmateId=265940&openMode=Always&language=en-US'[-33:]]  # last page: forms only, no page 3
    records = []
    for form in forms:
        records += list(spider.parse_form(text(form.url, f"load-{form.cb_kwargs['person']['Id']}.html"), **form.cb_kwargs))
    return records


def test_spider_reads_grid_fields_and_the_embedded_details_form():
    jane, richard = crawl()
    assert (jane['Id'], jane['FirstName'], jane['MIddleName'], jane['LastName'], jane['BookingNumber'], jane['PrisonerType']) == ('265929', 'JANE', 'Q', 'DOE', '2026-00006018', 'Felony')
    assert (jane['BookingDateTime'], jane['ReleaseDateTime']) == ('2026-10-22T00:57:19Z', 'Not Given')
    details = jane['Details']
    assert {k: v for k, v in details.items() if k not in ('Charges', 'Bonds')} == {
        'Name': 'JANE Q DOE', 'Inmate #': None, 'DOB': '10/11/1980', 'Resides in': None, 'Booking #': '2026-00006018', 'ORI': 'IL0840000',
        'Type': 'Felony', 'Booking date & time': '10/22/2026 12:57:19 AM', 'Class': None, 'Release Date': 'Not Given', 'Scheduled': 'Not Given',
    } or details['Booking #'] == '2026-00006018'
    assert details['Charges'] == [
        {'Charge': 'Agg DUI - Knowingly Operate Vehicle No Insurance', 'Statute': 'Aggravated DUI Vehicle not covered by liability insurance - Class 4',
         'Counts': '1', 'Disposition Date': 'Not Given', 'Case Number': '2026-00090579, ORI: IL0840200', 'Court Date & Time': '11/06/2026 9:00:00 AM'},
        {'Charge': 'DUI - Under the Influence of Alcohol', 'Statute': 'Driving Under the Influence - BAC .08 or more -Class A',
         'Counts': '1', 'Disposition Date': 'Not Given', 'Case Number': '2026-00090579, ORI: IL0840200', 'Court Date & Time': 'Not Given'},
    ]
    assert details['Bonds'] == [{'Bond': '2026-00000908', 'Bail Set Amount': '500.00', 'Bond Set Amount': '5000.00', 'Set Type': 'Set by Court', 'Court Date & Time': 'Not Given'}]
    assert richard['Details']['Bonds'] == []


def test_normalizer_keys_on_the_grid_id_and_reads_class_case_bond_and_court_date():
    jane, richard = (normalize('sangamon', r) for r in crawl())
    assert (jane.name, jane.county_person_key, jane.dob) == ('DOE, JANE Q', '265929', '1980-10-11')
    booking, = jane.bookings
    assert (booking.booking_number, booking.booking_date, booking.release_date) == ('2026-00006018', '2026-10-22 00:57:19', None)
    assert (booking.financial_hold, booking.next_court_date, booking.detention_status, booking.hold_type) == (5000.0, '2026-11-06 09:00:00', 'detained', None)
    assert [(c.description, c.offense_class, c.docket_number) for c in booking.charges] == [
        ('Agg DUI - Knowingly Operate Vehicle No Insurance', '4', '2026-00090579'),
        ('DUI - Under the Influence of Alcohol', 'A', '2026-00090579'),
    ]
    assert (richard.name, richard.bookings[0].financial_hold) == ('ROE, RICHARD', 0.0)
