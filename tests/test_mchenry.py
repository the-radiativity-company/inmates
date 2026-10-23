"""The McHenry spider and normalizer, run against a PDF laid out like the sheriff's in-custody report."""
from scrapy.http import Response

from inmates.loader import normalize
from inmates.scraper.spiders.mchenry import McHenrySpider
from tests.pdfs import pdf


URL = 'https://www.example.org/wp-content/uploads/pdf-uploads/InmateSearch_ByName.pdf'
FURNITURE = [
    (49, 64, 'This report contains only those subjects who have local McHenry County charges and who are 18 years of age or older.'),
    (107, 74, 'incarcerated in this facility, and that individual has federal charges, please contact the jail.'),
    (214, 84, '***All subjects are presumed innocent until proven guilty in a court of law***'),
    (31, 559, 'Although every effort is made to keep the information accurate and current, it cannot be guaranteed.'),
    (29, 590, 'Page 1 of 2'), (613, 590, 'Last Updated on 8/11/2026 11:00:08 PM'),
]
TABLE_HEADER = lambda y: [(55, y, 'Status'), (228, y, 'Charges'), (386, y, 'Class'), (432, y, 'Case #'), (498, y, 'Next Court Date'), (596, y, 'Court Room'), (662, y, 'Sentenced Release Date')]
LABELS = lambda y: [(278, y, 'Date Confined'), (393, y, 'Date of Birth'), (483, y, 'Age')]

PAGE_ONE = FURNITURE + [
    # a person flagged for a hold, whose flag is printed just above the name
    (527, 111, '**SUBJECT MAY HAVE A HOLD'), (541, 123, 'FOR ANOTHER AGENCY**'),
    (29, 113, 'DOE, JANE Q'), *LABELS(115),
    (260, 127, '02/06/2026 @ 3:00PM'), (398, 127, '04/21/1967'), (29, 128, 'JCA#: 154204'), (487, 129, '59'),
    (29, 147, 'CURRENTLY CONFINED'), (331, 166, 'Bond Is Set At $5,000.00'),
    *TABLE_HEADER(183),
    (54, 199, 'Waiting'), (112, 199, 'Aggravated Fleeing/Attempting to Elude Peace Officer - Rate of'), (395, 199, '4'), (423, 199, '2026CF460'),
    (485, 199, '08/20/2026 @ 9:00AM'), (614, 199, '304'), (680, 199, '**not applicable**'),
    (112, 209, 'Speed at Least 21 mph Over Speed Limit'),
    (40, 223, 'Remand for'), (112, 223, 'Possession of Controlled Substance'), (395, 223, '1'), (423, 223, '2025CF841'),
    (497, 223, '**not applicable**'), (608, 223, '**n/a**'), (680, 223, '**not applicable**'),
    (40, 233, 'Sentence'),
    (48, 247, 'Dismissed'), (112, 247, 'Possession of Drug Paraphernalia'), (395, 247, 'A'), (423, 247, '2025CF841'),
    (497, 247, '**not applicable**'), (608, 247, '**n/a**'), (680, 247, '**not applicable**'),
    # a person whose block runs over the page break, with a two-line name
    (29, 500, 'HERNANDEZ-HERNANDEZ,'), *LABELS(502), (29, 514, 'ARMANDO'),
    (260, 514, '09/24/2025 @ 5:25PM'), (398, 514, '04/25/1973'), (29, 515, 'JCA#: 153566'), (487, 516, '53'),
]
PAGE_TWO = FURNITURE + [
    (29, 113, 'CURRENTLY CONFINED'), (337, 131, 'No Bond At This Time'),
    *TABLE_HEADER(149),
    (40, 165, 'Sent to Prison'), (112, 165, 'Grooming'), (395, 165, '4'), (423, 165, '2026CF122'),
    (497, 165, '**not applicable**'), (608, 165, '**n/a**'), (667, 165, '08/19/2026 @ 12:00PM'),
    # someone released since the last report
    (29, 300, 'ROE, RICHARD'), *LABELS(302),
    (260, 314, '08/07/2026 @ 1:55PM'), (398, 314, '08/08/1966'), (29, 315, 'JCA#: 152765'), (487, 316, '60'),
    (29, 334, 'RECENTLY RELEASED ON 08/10/2026 @ 8:23AM - OTHER'),
]


def records():
    spider = McHenrySpider(domain=URL, county='mchenry')
    assert spider.start_urls == [URL]
    return list(spider.parse(Response(url=URL, body=pdf([PAGE_ONE, PAGE_TWO], width=792, height=612))))


def test_spider_reads_each_block_with_its_charges_across_wraps_and_page_breaks():
    jane, armando, richard = records()
    assert {k: v for k, v in jane.items() if k != 'Charges'} == {
        'Name': 'DOE, JANE Q', 'JCA#': '154204', 'Date Confined': '02/06/2026 @ 3:00PM', 'Date of Birth': '04/21/1967', 'Age': '59',
        'Custody': 'CURRENTLY CONFINED', 'Bond': 'Bond Is Set At $5,000.00', 'Hold': 'SUBJECT MAY HAVE A HOLD FOR ANOTHER AGENCY',
    }
    assert jane['Charges'] == [
        {'Status': 'Waiting', 'Charge': 'Aggravated Fleeing/Attempting to Elude Peace Officer - Rate of Speed at Least 21 mph Over Speed Limit',
         'Class': '4', 'Case #': '2026CF460', 'Next Court Date': '08/20/2026 @ 9:00AM', 'Court Room': '304', 'Sentenced Release Date': '**not applicable**'},
        {'Status': 'Remand for Sentence', 'Charge': 'Possession of Controlled Substance', 'Class': '1', 'Case #': '2025CF841',
         'Next Court Date': '**not applicable**', 'Court Room': '**n/a**', 'Sentenced Release Date': '**not applicable**'},
        {'Status': 'Dismissed', 'Charge': 'Possession of Drug Paraphernalia', 'Class': 'A', 'Case #': '2025CF841',
         'Next Court Date': '**not applicable**', 'Court Room': '**n/a**', 'Sentenced Release Date': '**not applicable**'},
    ]
    assert (armando['Name'], armando['JCA#'], armando['Custody'], armando['Bond']) == ('HERNANDEZ-HERNANDEZ, ARMANDO', '153566', 'CURRENTLY CONFINED', 'No Bond At This Time')
    assert [c['Status'] for c in armando['Charges']] == ['Sent to Prison']
    assert 'Hold' not in armando
    assert (richard['Custody'], richard['Charges'], 'Bond' in richard) == ('RECENTLY RELEASED ON 08/10/2026 @ 8:23AM - OTHER', [], False)


def test_normalizer_reads_bond_hold_sentence_and_release():
    jane, armando, richard = (normalize('mchenry', r) for r in records())
    assert (jane.name, jane.county_person_key, jane.dob, jane.age) == ('DOE, JANE Q', '154204', '1967-04-21', 59)
    booking, = jane.bookings
    assert (booking.booking_number, booking.booking_date, booking.next_court_date) == ('154204', '2026-02-06 15:00:00', '2026-08-20 09:00:00')
    assert (booking.financial_hold, booking.detention_status, booking.hold_type) == (5000.0, 'hold', 'hold')
    assert [(c.offense_class, c.docket_number) for c in booking.charges] == [('4', '2026CF460'), ('1', '2025CF841'), ('A', '2025CF841')]

    booking, = armando.bookings
    assert (booking.financial_hold, booking.detention_status, booking.hold_type) == (0.0, 'sentenced', None)

    booking, = richard.bookings
    assert (booking.release_date, booking.detention_status, booking.financial_hold) == ('2026-08-10 08:23:00', 'released', None)
