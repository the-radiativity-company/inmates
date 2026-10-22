"""The NewWorld platform spider, run against saved copies of its two page types."""
from pathlib import Path

from scrapy import Request
from scrapy.http import HtmlResponse

from inmates.scraper.spiders.newworld import NewWorldSpider


FIXTURES = Path(__file__).parent / 'fixtures' / 'newworld'
ROOT = 'http://jail.example/NewWorld.InmateInquiry/example'


def response_from(name: str, url: str) -> HtmlResponse:
    return HtmlResponse(url=url, body=(FIXTURES / name).read_bytes(), encoding='utf-8')


def test_start_url_insists_on_in_custody():
    spider = NewWorldSpider(domain=f'{ROOT}?Name=&SubjectNumber=&Facility=', county='example')
    assert spider.start_urls == [f'{ROOT}?InCustody=True']
    assert NewWorldSpider(domain=f'{ROOT}/', county='example').start_urls == [f'{ROOT}?InCustody=True']


def test_index_follows_every_detail_link_and_the_next_page():
    spider = NewWorldSpider(domain=ROOT, county='example')
    requests = list(spider.parse(response_from('index.html', f'{ROOT}?InCustody=True')))
    assert all(isinstance(r, Request) for r in requests)
    by_callback = {}
    for r in requests:
        by_callback.setdefault(r.callback.__name__, []).append(r.url)
    assert by_callback['parse_detail'] == [f'{ROOT}/Inmate/Detail/-1001', f'{ROOT}/Inmate/Detail/-1002']
    assert by_callback['parse'] == [f'{ROOT}?InCustody=True&Page=2']


def test_index_pager_may_be_a_nav():
    spider = NewWorldSpider(domain=ROOT, county='example')
    html = (FIXTURES / 'index.html').read_text().replace('<div class="Pager">', '<nav class="Pager">').replace('</a>\n</div>\n</div>\n<div class="ContentEnd">', '</a>\n</nav>\n</div>\n<div class="ContentEnd">')
    response = HtmlResponse(url=f'{ROOT}?InCustody=True', body=html.encode(), encoding='utf-8')
    assert [r.url for r in spider.parse(response) if r.callback.__name__ == 'parse'] == [f'{ROOT}?InCustody=True&Page=2']


def test_detail_yields_one_record_with_nested_bookings():
    spider = NewWorldSpider(domain=ROOT, county='example')
    record, = spider.parse_detail(response_from('detail.html', f'{ROOT}/Inmate/Detail/-1001'))

    assert record['Name'] == 'DOE, JANE'
    assert record['Subject Number'] == '10001'
    assert record['Detail Id'] == '-1001'
    assert record['Address'] == '1 MAIN ST ANYTOWN, ILLINOIS 60000'
    assert record['Aliases'] is None

    booking, = record['Bookings']
    assert booking['Booking Number'] == '2026-00001964'
    assert booking['Booking Date'] == '10/22/2026 4:01 AM'
    assert booking['Release Date'] is None
    assert booking['Prisoner Type'] == 'NEW CHARGES - ADULT'
    assert booking['Bonds'] == []
    assert [c['Court Date'] for c in booking['Court Dates']] == ['10/22/2026 1:00 PM', '11/05/2026 9:00 AM']
    assert [c['Charge Description'] for c in booking['Charges']] == ['DOMESTIC BATTERY - BODILY HARM (MIS)', 'FUGITIVE WARRANT']
    assert booking['Charges'][1]['Docket Number'] == 'KANSAS HOLD'
    assert booking['Charges'][0]['Crime Class'] == 'PART I VIOLENT CRIME'
