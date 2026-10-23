"""Loader tests run against synthetic records shaped like each roster's real output."""
import pytest

from inmates.loader import connect
from inmates.loader import load_county
from inmates.loader import normalize


# the NewWorld InmateInquiry detail shape (Macon, Kendall, Kankakee, Will)
MACON = [
    {'Name': 'DOE, JANE', 'Subject Number': '10001', 'Age': '37', 'Gender': 'FEMALE', 'Race': 'WHITE',
     'Height': "5' 4\"", 'Weight': '130.0 lbs', 'Address': 'ANYTOWN, ILLINOIS 60000', 'Aliases': None,
     'Bookings': [
         {'Booking Number': '2026-00001964', 'Booking Date': '10/22/2026 4:01 AM', 'Release Date': None,
          'Scheduled Release Date': None, 'Prisoner Type': 'NEW CHARGES - ADULT',
          'Housing Facility': 'MACON COUNTY JAIL', 'Total Bond Amount': '$0.00', 'Total Bail Amount': '$0.00',
          'Booking Origin': 'DECATUR POLICE DEPARTMENT', 'Bonds': [],
          'Court Dates': [{'Charges': '1', 'Court Date': '10/22/2026 1:00 PM', 'Court': 'MACON COUNTY', 'Court Room': '3B'}],
          'Charges': [{'Number': '1', 'Charge Description': 'DOMESTIC BATTERY - BODILY HARM (MIS)',
                       'Offense Date': '10/22/2026 4:05 AM', 'Docket Number': None, 'Crime Class': 'Class A',
                       'Arresting Agency': 'DECATUR POLICE DEPARTMENT', 'Attempt/Commit': 'COMMITTED', 'Bond': None}]},
     ]},
    {'Name': 'ROE, RICHARD', 'Subject Number': '10002', 'Age': '51', 'Gender': 'MALE', 'Race': 'BLACK', 'Bookings': []},
]

WILL = [
    {'Name': 'DOE, JOHN', 'Subject Number': None, 'Age': '30', 'Gender': 'MALE', 'Race': 'WHITE',
     'Height': "6' 0\"", 'Weight': '180.0 lbs',
     'Bookings': [
         {'Booking Number': '2020-00009001', 'Booking Date': '11/22/2020 6:37 AM', 'Release Date': None,
          'Housing Facility': 'WILL COUNTY ADULT DETENTION FACILITY',
          'Total Bond Amount': '$30,000.00', 'Total Bail Amount': '$3,000.00',
          'Booking Origin': 'JOLIET POLICE DEPARTMENT',
          'Bonds': [{'Bond Number': '2020-1', 'Bond Type': '10%', 'Bond Amount': '$30,000.00'}],
          'Court Dates': [{'Charges': '1', 'Court Date': '11/24/2020 10:30 AM', 'Court': 'WILL COUNTY', 'Court Room': '410'},
                          {'Charges': '2', 'Court Date': '12/15/2020 9:00 AM', 'Court': 'WILL COUNTY', 'Court Room': '410'}],
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

ADAMS = [{'Name': 'EXAMPLE, PAT', 'AC #': '10101', 'Charges': '720-5/16-25 - Retail Theft', 'Bond': None, 'Court Date': '11/10/26', 'Time': '09:30', 'Courtroom': 'Court Room 1A', 'Arrest Type': 'New Arrest', 'Printed': 'October 22, 2026'}]

T1, T2, T3 = '2026-10-21 06:12:00', '2026-10-22 06:12:00', '2026-10-23 06:12:00'


@pytest.fixture
def conn():
    c = connect(':memory:')
    yield c
    c.close()


def one(conn, sql, *params):
    return conn.execute(sql, params).fetchone()


def test_newworld_normalizer_keys_on_subject_number():
    p = normalize('macon', MACON[0], 'newworld')
    assert (p.name, p.county_person_key, p.sex, p.race, p.facility) == ('DOE, JANE', '10001', 'F', 'WHITE', 'MACON COUNTY JAIL')
    booking, = p.bookings
    assert (booking.booking_number, booking.next_court_date) == ('2026-00001964', '2026-10-22 13:00:00')
    assert (booking.detention_status, booking.hold_type, booking.financial_hold) == ('detained', None, 0.0)
    assert booking.charges[0].offense_class == 'Class A'
    assert p.raw is MACON[0]
    assert normalize('macon', MACON[1], 'newworld').bookings == []


def test_newworld_prisoner_type_marks_sentenced_people():
    record = dict(MACON[0], Bookings=[dict(MACON[0]['Bookings'][0], **{'Prisoner Type': 'SENTENCED- WORK RELEASE'})])
    assert normalize('macon', record, 'newworld').bookings[0].detention_status == 'sentenced'


def test_newworld_normalizer_builds_bookings_and_charges():
    p = normalize('will', WILL[0], 'newworld')
    assert (p.name, p.county_person_key, p.age, p.sex) == ('DOE, JOHN', 'doe, john', 30, 'M')
    assert normalize('will', dict(WILL[0], **{'Detail Id': '-499749'}), 'newworld').county_person_key == '-499749'
    assert p.facility == 'WILL COUNTY ADULT DETENTION FACILITY'
    open_booking, closed_booking = p.bookings
    assert open_booking.booking_date == '2020-11-22 06:37:00'
    assert open_booking.next_court_date == '2020-12-15 09:00:00'
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


def test_platform_wins_over_county_and_unknown_platform_falls_through():
    assert normalize('kendall', MACON[0], 'newworld').county_person_key == '10001'
    assert normalize('stclair', STCLAIR[0], 'nosuchplatform').dob == '1993-09-25'


def test_generic_normalizer_for_unknown_county():
    p = normalize('nowhere', {'Full Name:': 'X Y', 'Thing': 1})
    assert p.name == 'X Y'
    assert p.raw == {'Full Name:': 'X Y', 'Thing': 1}


def test_load_creates_rows(conn):
    r = load_county(conn, 'will', WILL, T1, 'http://example.test/will', 'newworld')
    assert (r.status, r.loaded, r.released) == ('ok', 1, 0)
    assert one(conn, 'SELECT count(*) FROM person')[0] == 1
    assert one(conn, 'SELECT count(*) FROM booking')[0] == 2
    assert one(conn, 'SELECT count(*) FROM charge')[0] == 3
    assert one(conn, 'SELECT status, record_count FROM scrape_run') == ('ok', 1)
    assert one(conn, 'SELECT source_url, first_seen, last_seen FROM person') == ('http://example.test/will', T1, T1)


def test_absent_person_leaves_custody_on_next_successful_scrape(conn):
    load_county(conn, 'macon', MACON, T1, platform='newworld')
    r = load_county(conn, 'macon', MACON[:1], T2, platform='newworld')
    assert r.released == 1
    rows = dict(conn.execute('SELECT county_person_key, in_custody FROM person').fetchall())
    assert rows == {'10001': 1, '10002': 0}
    assert one(conn, "SELECT first_seen, last_seen FROM person WHERE county_person_key = '10001'") == (T1, T2)
    assert one(conn, "SELECT last_seen FROM person WHERE county_person_key = '10002'") == (T1,)


def test_returning_person_is_back_in_custody_with_original_first_seen(conn):
    load_county(conn, 'macon', MACON, T1, platform='newworld')
    load_county(conn, 'macon', MACON[:1], T2, platform='newworld')
    load_county(conn, 'macon', MACON, T3, platform='newworld')
    assert one(conn, "SELECT in_custody, first_seen, last_seen FROM person WHERE county_person_key = '10002'") == (1, T1, T3)


def test_empty_or_missing_scrape_does_not_release_anyone(conn):
    load_county(conn, 'macon', MACON, T1, platform='newworld')
    empty = load_county(conn, 'macon', [], T2, platform='newworld')
    missing = load_county(conn, 'macon', None, T3, platform='newworld')
    assert (empty.status, missing.status) == ('empty', 'missing')
    assert one(conn, 'SELECT count(*) FROM person WHERE in_custody = 1')[0] == 2
    assert [r[0] for r in conn.execute('SELECT status FROM scrape_run ORDER BY scraped_at')] == ['ok', 'empty', 'missing']


def test_reloading_the_same_scrape_is_a_no_op(conn):
    load_county(conn, 'will', WILL, T1, platform='newworld')
    r = load_county(conn, 'will', WILL, T1, platform='newworld')
    assert r.status == 'duplicate'
    assert one(conn, 'SELECT count(*) FROM booking')[0] == 2


def test_bookings_are_replaced_not_accumulated(conn):
    load_county(conn, 'will', WILL, T1, platform='newworld')
    load_county(conn, 'will', WILL, T2, platform='newworld')
    assert one(conn, 'SELECT count(*) FROM booking')[0] == 2
    assert one(conn, 'SELECT count(*) FROM charge')[0] == 3


def test_current_custody_view(conn):
    load_county(conn, 'will', WILL, T1, platform='newworld')
    load_county(conn, 'stclair', STCLAIR, T1)
    load_county(conn, 'adams', ADAMS, T1)
    rows = conn.execute('SELECT county, name, detention_status, hold_type, charges FROM current_custody ORDER BY county').fetchall()
    assert rows == [
        ('adams', 'EXAMPLE, PAT', 'detained', None, '720-5/16-25 Retail Theft'),
        ('stclair', 'DOE JANE Q.', 'hold', 'warrant', '720 ILCS 5/9-1 FIRST DEGREE MURDER; 720 ILCS 5/32-10(A) IN STATE WARRANT'),
        ('will', 'DOE, JOHN', 'hold', 'out_of_state', 'FUGITIVE WARRANT; RETAIL THEFT'),
    ]


def test_person_the_roster_lists_as_released_is_loaded_but_not_in_custody(conn):
    gone = {'Name': 'GONE, GILLIAN', 'Subject Number': '10009', 'Age': '40', 'Gender': 'FEMALE', 'Race': 'WHITE',
            'Bookings': [{'Booking Number': '2026-9', 'Booking Date': '10/01/2026 9:00 AM', 'Release Date': '10/21/2026 3:00 PM',
                          'Prisoner Type': 'NEW CHARGES - ADULT', 'Bonds': [], 'Court Dates': [], 'Charges': []}]}
    result = load_county(conn, 'macon', MACON + [gone], '2026-10-22T06:00:00', platform='newworld')
    assert (result.loaded, result.released) == (3, 1)
    assert conn.execute("SELECT in_custody FROM person WHERE county_person_key = '10009'").fetchone() == (0,)
    assert conn.execute("SELECT COUNT(*) FROM booking b JOIN person p ON p.id = b.person_id WHERE p.county_person_key = '10009'").fetchone() == (1,)
    assert 'GONE, GILLIAN' not in [row[0] for row in conn.execute('SELECT name FROM current_custody')]
    assert conn.execute("SELECT COUNT(*) FROM current_custody WHERE county = 'macon'").fetchone() == (2,)

