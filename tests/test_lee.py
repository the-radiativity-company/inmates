"""The Lee spider and normalizer, run against a PDF laid out like the sheriff's inmate list."""
from scrapy.http import Response

from inmates.loader import normalize
from inmates.scraper.spiders.lee import LeeSpider
from tests.pdfs import pdf


URL = 'https://www.example.com/DocumentCenter/View/2814'
PAGE_ONE = [
    (122, 57, "LEE COUNTY SHERIFF'S"), (122, 84, 'DEPARTMENT'), (122, 109, 'Current Inmate List, by Name'),
    (54, 148, 'Name'), (414, 148, 'Booking #'),
    (54, 160, 'DOE, JANE Q'), (414, 160, '26LJ-0640'),
    (54, 172, 'ROE, RICHARD'), (414, 172, '23LJ-0129'),
    (54, 740, 'rpjlcil.x2'), (300, 740, '10/22/26'),
]
PAGE_TWO = [
    (122, 109, 'Current Inmate List, by Name'),
    (54, 148, 'Name'), (414, 148, 'Booking #'),
    (54, 160, 'POE, PAT'), (414, 160, '26LJ-1109'),
    (54, 190, 'Total Housed Inmates: 3'),
    (54, 740, 'rpjlcil.x2'), (300, 740, '10/22/26'),
]


def records():
    spider = LeeSpider(domain=URL, county='lee')
    assert spider.start_urls == [URL]
    return list(spider.parse(Response(url=URL, body=pdf([PAGE_ONE, PAGE_TWO]))))


def test_spider_pairs_each_name_with_its_booking_number_across_pages():
    assert records() == [
        {'Name': 'DOE, JANE Q', 'Booking #': '26LJ-0640', 'Report Date': '10/22/26'},
        {'Name': 'ROE, RICHARD', 'Booking #': '23LJ-0129', 'Report Date': '10/22/26'},
        {'Name': 'POE, PAT', 'Booking #': '26LJ-1109', 'Report Date': '10/22/26'},
    ]


def test_normalizer_keys_on_the_booking_number():
    jane, *_ = (normalize('lee', r) for r in records())
    assert (jane.name, jane.county_person_key, jane.age) == ('DOE, JANE Q', '26LJ-0640', None)
    booking, = jane.bookings
    assert (booking.booking_number, booking.booking_date, booking.detention_status, booking.financial_hold) == ('26LJ-0640', None, 'detained', None)
