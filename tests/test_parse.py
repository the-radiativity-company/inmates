from inmates.loader.parse import clean_text
from inmates.loader.parse import hold_type_for
from inmates.loader.parse import iso_date
from inmates.loader.parse import iso_datetime
from inmates.loader.parse import parse_money
from inmates.loader.parse import split_statute


def test_clean_text_strips_markup_and_whitespace():
    assert clean_text('<td class="Name"><a href="/x">DOE,  JANE</a></td>') == 'DOE, JANE'
    assert clean_text('   ') is None
    assert clean_text(None) is None


def test_datetime_formats_seen_on_rosters():
    assert iso_datetime('11/22/2020 6:37 AM') == '2020-11-22 06:37:00'
    assert iso_datetime('11-24-2020 - 12:02 am') == '2020-11-24 00:02:00'
    assert iso_datetime('Sunday September 08, 2019 at  9:41 pm.  (423 days in custody)') == '2019-09-08 21:41:00'
    assert iso_datetime('Next Court: Tuesday November 24, 2020 @ 10:30 am, Room 410, Status Conference') == '2020-11-24 10:30:00'
    assert iso_date('9/25/1993') == '1993-09-25'
    assert iso_datetime('not a date') is None
    assert iso_datetime(None) is None


def test_money():
    assert parse_money('$30,000.00') == 30000.0
    assert parse_money('502500') == 502500.0
    assert parse_money('$3000') == 3000.0
    assert parse_money('0') == 0.0
    assert parse_money('no bond') is None


def test_statute_split():
    assert split_statute('720 ILCS 5/9-1 FIRST DEGREE MURDER') == ('720 ILCS 5/9-1', 'FIRST DEGREE MURDER')
    assert split_statute('720 ILCS 5/32-10(a) IN STATE WARRANT') == ('720 ILCS 5/32-10(A)', 'IN STATE WARRANT')
    assert split_statute('RECKLESS ENDANGERMENT') == (None, 'RECKLESS ENDANGERMENT')


def test_hold_types():
    assert hold_type_for('Inmate has Hold Orders, Can Not Be Released on Bond') == 'hold'
    assert hold_type_for('FUGITIVE WARRANT', 'KANSAS HOLD') == 'out_of_state'
    assert hold_type_for('720 ILCS 5/3-3-9 PAROLE VIOLATION') == 'doc'
    assert hold_type_for('US MARSHAL HOLD') == 'federal'
    assert hold_type_for('IN STATE WARRANT') == 'warrant'
    assert hold_type_for('RETAIL THEFT', None) is None
