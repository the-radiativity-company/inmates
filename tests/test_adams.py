"""The Adams spider and normalizer, run against a page like the sheriff's and a PDF laid out like the population report."""
from scrapy.http import HtmlResponse
from scrapy.http import Response

from inmates.loader import normalize
from inmates.scraper.spiders.adams import AdamsSpider
from tests.pdfs import pdf


URL = 'https://www.example.gov/government/departments/sheriff-jail/county-jail/jail-inmate-list'
HEADINGS = lambda: [(49, 113, 'Population'), (605, 113, 'Printed on October 22, 2026'), (49, 142, 'Front Mugshot'), (139, 142, 'Last, First Name'),
                    (259, 142, 'Charges'), (433, 142, 'Bond'), (499, 142, 'Court Date'), (559, 142, 'Time'), (601, 142, 'Courtroom')]
PAGE_ONE = HEADINGS() + [
    (139, 180, 'DOE, JANE'), (259, 180, '720-5/11-20.1 - Child Pornography'), (433, 180, '$1003.00'), (499, 180, '11/10/26'), (559, 180, '10:30'), (601, 180, 'Court Room 2B'),
    (139, 192, 'AC #'), (169, 192, '29330'),
    (139, 240, 'ROE, RICHARD'), (259, 240, '720-5/24-1.2 - Aggravated Discharge of a'), (259, 250, 'Firearm'),
    (139, 252, 'AC #'), (169, 252, '13062'), (601, 258, 'IDOC Writ'),
    # a long last name is printed alone with its first name clipped, and the row runs over the page break
    (139, 404, 'LAWTON-HUFFORD,'), (259, 404, '720-5/31-1(a) - Resisting or Obstructing Peace'), (499, 404, '11/03/26'), (559, 404, '14:30'), (601, 404, 'Court Room 1B'),
    (259, 414, 'Officer; 720-5/16-1(a)(1) - Theft - Obtains/Exerts'),
    (139, 416, 'AC #'), (169, 416, '24248'), (601, 422, 'Warrant Arrest'),
    (686, 565, 'Page 1 of 2'),
]
PAGE_TWO = HEADINGS() + [
    (259, 180, 'Unauthorized Control Over Property of the Owner Less Than $500'),
    (139, 240, 'POE, PAT'), (259, 240, '720-5/12-3.2(a)(1) - Domestic Battery'), (433, 240, '$0.00'), (601, 246, 'Sentence'),
    (139, 252, 'AC #'), (169, 252, '26567'),
    (49, 530, 'Total Records: 4'), (686, 565, 'Page 2 of 2'),
]


def records():
    spider = AdamsSpider(domain=URL, county='adams')
    assert spider.start_urls == [URL]
    request, = spider.parse(HtmlResponse(url=URL, body=open('tests/fixtures/adams-list.html', 'rb').read(), encoding='utf-8'))
    assert request.url == 'https://www.example.gov/Home/ShowDocument?id=5357'
    return list(spider.parse_pdf(Response(url=request.url, body=pdf([PAGE_ONE, PAGE_TWO], width=792, height=612))))


def test_spider_reads_a_row_per_person_across_wrapped_charges_names_and_pages():
    jane, richard, pat_lh, pat = records()
    assert jane == {'Name': 'DOE, JANE', 'AC #': '29330', 'Charges': '720-5/11-20.1 - Child Pornography', 'Bond': '$1003.00', 'Court Date': '11/10/26',
                    'Time': '10:30', 'Courtroom': 'Court Room 2B', 'Arrest Type': None, 'Printed': 'October 22, 2026'}
    assert (richard['Charges'], richard['Arrest Type'], richard['Bond'], richard['Court Date']) == ('720-5/24-1.2 - Aggravated Discharge of a Firearm', 'IDOC Writ', None, None)
    assert (pat_lh['Name'], pat_lh['AC #'], pat_lh['Arrest Type']) == ('LAWTON-HUFFORD,', '24248', 'Warrant Arrest')
    assert pat_lh['Charges'] == '720-5/31-1(a) - Resisting or Obstructing Peace Officer; 720-5/16-1(a)(1) - Theft - Obtains/Exerts Unauthorized Control Over Property of the Owner Less Than $500'
    assert (pat['Name'], pat['Bond'], pat['Arrest Type'], pat['Courtroom']) == ('POE, PAT', '$0.00', 'Sentence', None)


def test_normalizer_splits_statutes_and_reads_bond_court_date_and_arrest_type():
    jane, richard, pat_lh, pat = (normalize('adams', r) for r in records())
    assert (jane.name, jane.county_person_key) == ('DOE, JANE', '29330')
    booking, = jane.bookings
    assert (booking.financial_hold, booking.next_court_date, booking.detention_status, booking.hold_type) == (1003.0, '2026-11-10 10:30:00', 'detained', None)
    assert [(c.statute, c.description) for c in booking.charges] == [('720-5/11-20.1', 'Child Pornography')]

    assert (richard.bookings[0].detention_status, richard.bookings[0].hold_type, richard.bookings[0].financial_hold) == ('hold', 'doc', None)
    assert [(c.statute, c.description) for c in pat_lh.bookings[0].charges] == [
        ('720-5/31-1(a)', 'Resisting or Obstructing Peace Officer'),
        ('720-5/16-1(a)(1)', 'Theft - Obtains/Exerts Unauthorized Control Over Property of the Owner Less Than $500'),
    ]
    assert (pat_lh.name, pat_lh.bookings[0].detention_status, pat_lh.bookings[0].hold_type) == ('LAWTON-HUFFORD', 'detained', None)
    assert (pat.bookings[0].detention_status, pat.bookings[0].financial_hold) == ('sentenced', 0.0)
