"""Loader tests run against synthetic records shaped like each county's real output."""
import pytest

from inmates.loader import connect
from inmates.loader import load_county
from inmates.loader import normalize


MACON = [
    {'Photo': '<td class="Photo"><img src="/p/1"></td>',
     'Name': '<td class="Name"><a href="/Detail/-1">DOE, JANE</a></td>',
     'SubjectNumber': '10001', 'InCustody': None, 'ScheduledReleaseDate': None,
     'Race': 'White', 'Gender': 'Female', 'Height': "5' 4\"", 'Weight': '130.0 lbs',
     'MultipleBookings': None, 'HousingFacility': None},
    {'Photo': None, 'Name': '<td class="Name"><a href="/Detail/-2">ROE, RICHARD</a></td>',
     'SubjectNumber': '10002', 'Race': 'Black', 'Gender': 'Male'},
]

WILL = [
    {'Name': 'DOE, JOHN', 'Age': '30', 'Gender': 'MALE', 'Race': 'WHITE', 'Height': "6' 0\"", 'Weight': '180.0 lbs',
     'Bookings': [
         {'Booking Date': '11/22/2020 6:37 AM', 'Release Date': None,
          'Housing Facility': 'WILL COUNTY ADULT DETENTION FACILITY',
          'Total Bond Amount': '$30,000.00', 'Total Bail Amount': '$3,000.00',
          'Booking Origin': 'JOLIET POLICE DEPARTMENT',
          'Bonds': [{'Bond Number': '2020-1', 'Bond Type': '10%', 'Bond Amount': '$30,000.00'}],
          'Charges': [
              {'Number': '2', 'Charge Description': 'FUGITIVE WARRANT', 'Offense Date': '11/22/2020 7:52 AM',
               'Docket Number': 'KANSAS HOLD', 'Arresting Agency': 'COMMIT'},
              {'Number': '1', 'Charge Description': 'RETAIL THEFT', 'Offense Date': '11/22/2020 7:45 AM',
               'Docket Number': '20CF1', 'Arresting Agency': 'COMMIT'}]},
         {'Booking Date': '1/14/2019 2:49 AM', 'Release Date': '7/7/2020 1:44 PM', 'Housing Facility': None,
          'Total Bond Amount': '$0.00', 'Booking Origin': 'WILL COUNTY SHERIFF',
          'Bonds': [], 'Charges': [{'Number': '1', 'Charge Description': 'CRIMINAL TRESPASS TO LAND',
                                    'Offense Date': '11/14/2018 12:00 AM', 'Docket Number': '2018CM1'}]},
     ]},
]

STCLAIR = [
    {'Name:': 'DOE JANE Q.', 'DOB:': '9/25/1993', 'Age:': '27', 'Booking Number:': '20190-5588',
     'Booking Date:': 'Sunday September 08, 2019 at  9:41 pm.  (423 days in custody)',
     'Booking Type:': 'NEW OFFENSE (FELONY - FEMALE)', 'Bond Amount:': '502500',
     'Bond Details:': 'Bond is Set at $502,500.00, cash amount for release is $50,250.00.',
     'Gender:': 'Female', 'Race:': 'BLACK',
     'Next Court Date:': 'Next Court: Tuesday November 24, 2020 @ 10:30 am, Room 410, Status Conference',
     'Charges': ['720 ILCS 5/9-1 FIRST DEGREE MURDER', '720 ILCS 5/32-10(a) IN STATE WARRANT']},
]

DEKALB = [
    {'Inmate Id:': '50267', 'Age:': '25', 'Gender:': 'M', 'Race:': 'WHITE', 'Address:': ' SOMEWHERE ,  IL ',
     'Arresting Agency:': 'OTHER', 'Booking Date:': '11-24-2020 - 12:02 am',
     'Charges': ['RECKLESS ENDANGERMENT', 'ATTEMPT TO ELUDE'], 'Bond:': '$3000'},
]

ADAMS = [{'name': 'Pat Example', 'gender': None, 'age': None, 'race': None, 'bookings': {}}]

T1, T2, T3 = '2026-10-21 06:12:00', '2026-10-22 06:12:00', '2026-10-23 06:12:00'


@pytest.fixture
def conn():
    c = connect(':memory:')
    yield c
    c.close()


def one(conn, sql, *params):
    return conn.execute(sql, params).fetchone()


def test_macon_normalizer_strips_html_and_keys_on_subject_number():
    p = normalize('macon', MACON[0])
    assert (p.name, p.county_person_key, p.sex, p.race) == ('DOE, JANE', '10001', 'F', 'WHITE')
    assert p.bookings == []
    assert p.raw is MACON[0]


def test_will_normalizer_builds_bookings_and_charges():
    p = normalize('will', WILL[0])
    assert (p.name, p.age, p.sex, p.facility) == ('DOE, JOHN', 30, 'M', 'WILL COUNTY ADULT DETENTION FACILITY')
    open_booking, closed_booking = p.bookings
    assert open_booking.booking_date == '2020-11-22 06:37:00'
    assert open_booking.financial_hold == 30000.0
    assert open_booking.hold_type == 'out_of_state'
    assert open_booking.detention_status == 'hold'
    assert [c.description for c in open_booking.charges] == ['FUGITIVE WARRANT', 'RETAIL THEFT']
    assert closed_booking.release_date == '2020-07-07 13:44:00'
    assert closed_booking.detention_status == 'released'


def test_stclair_normalizer_parses_statutes_and_court_date():
    p = normalize('stclair', STCLAIR[0])
    assert p.dob == '1993-09-25'
    assert p.county_person_key == 'doe jane q.|1993-09-25'
    [b] = p.bookings
    assert b.booking_number == '20190-5588'
    assert b.booking_date == '2019-09-08 21:41:00'
    assert b.next_court_date == '2020-11-24 10:30:00'
    assert b.financial_hold == 502500.0
    assert b.charges[0].statute == '720 ILCS 5/9-1'
    assert b.charges[0].description == 'FIRST DEGREE MURDER'
    assert b.hold_type == 'warrant'


def test_dekalb_normalizer():
    p = normalize('dekalb', DEKALB[0])
    assert p.county_person_key == '50267'
    [b] = p.bookings
    assert b.booking_date == '2020-11-24 00:02:00'
    assert b.financial_hold == 3000.0
    assert b.detention_status == 'detained'
    assert [c.statute for c in b.charges] == [None, None]


def test_generic_normalizer_for_unknown_county():
    p = normalize('nowhere', {'Full Name:': 'X Y', 'Thing': 1})
    assert p.name == 'X Y'
    assert p.raw == {'Full Name:': 'X Y', 'Thing': 1}


def test_load_creates_rows(conn):
    r = load_county(conn, 'will', WILL, T1, 'http://example.test/will')
    assert (r.status, r.loaded, r.released) == ('ok', 1, 0)
    assert one(conn, 'SELECT count(*) FROM person')[0] == 1
    assert one(conn, 'SELECT count(*) FROM booking')[0] == 2
    assert one(conn, 'SELECT count(*) FROM charge')[0] == 3
    assert one(conn, 'SELECT status, record_count FROM scrape_run') == ('ok', 1)
    assert one(conn, 'SELECT source_url, first_seen, last_seen FROM person') == ('http://example.test/will', T1, T1)


def test_absent_person_leaves_custody_on_next_successful_scrape(conn):
    load_county(conn, 'macon', MACON, T1)
    r = load_county(conn, 'macon', MACON[:1], T2)
    assert r.released == 1
    rows = dict(conn.execute('SELECT county_person_key, in_custody FROM person').fetchall())
    assert rows == {'10001': 1, '10002': 0}
    assert one(conn, "SELECT first_seen, last_seen FROM person WHERE county_person_key = '10001'") == (T1, T2)
    assert one(conn, "SELECT last_seen FROM person WHERE county_person_key = '10002'") == (T1,)


def test_returning_person_is_back_in_custody_with_original_first_seen(conn):
    load_county(conn, 'macon', MACON, T1)
    load_county(conn, 'macon', MACON[:1], T2)
    load_county(conn, 'macon', MACON, T3)
    assert one(conn, "SELECT in_custody, first_seen, last_seen FROM person WHERE county_person_key = '10002'") == (1, T1, T3)


def test_empty_or_missing_scrape_does_not_release_anyone(conn):
    load_county(conn, 'macon', MACON, T1)
    empty = load_county(conn, 'macon', [], T2)
    missing = load_county(conn, 'macon', None, T3)
    assert (empty.status, missing.status) == ('empty', 'missing')
    assert one(conn, 'SELECT count(*) FROM person WHERE in_custody = 1')[0] == 2
    assert [r[0] for r in conn.execute('SELECT status FROM scrape_run ORDER BY scraped_at')] == ['ok', 'empty', 'missing']


def test_reloading_the_same_scrape_is_a_no_op(conn):
    load_county(conn, 'will', WILL, T1)
    r = load_county(conn, 'will', WILL, T1)
    assert r.status == 'duplicate'
    assert one(conn, 'SELECT count(*) FROM booking')[0] == 2


def test_bookings_are_replaced_not_accumulated(conn):
    load_county(conn, 'will', WILL, T1)
    load_county(conn, 'will', WILL, T2)
    assert one(conn, 'SELECT count(*) FROM booking')[0] == 2
    assert one(conn, 'SELECT count(*) FROM charge')[0] == 3


def test_current_custody_view(conn):
    load_county(conn, 'will', WILL, T1)
    load_county(conn, 'stclair', STCLAIR, T1)
    load_county(conn, 'adams', ADAMS, T1)
    rows = conn.execute('SELECT county, name, detention_status, hold_type, charges FROM current_custody ORDER BY county').fetchall()
    assert rows == [
        ('adams', 'Pat Example', None, None, None),
        ('stclair', 'DOE JANE Q.', 'hold', 'warrant', '720 ILCS 5/9-1 FIRST DEGREE MURDER; 720 ILCS 5/32-10(A) IN STATE WARRANT'),
        ('will', 'DOE, JOHN', 'hold', 'out_of_state', 'FUGITIVE WARRANT; RETAIL THEFT'),
    ]
