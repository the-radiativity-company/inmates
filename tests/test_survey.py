"""Survey tests stand in for the network with canned responses."""
from io import BytesIO
from urllib.error import HTTPError
from urllib.error import URLError

import pytest

from inmates import survey as module
from inmates.rosters import COLUMNS
from inmates.rosters import read_index
from inmates.rosters import write_index
from inmates.survey import detect_platform
from inmates.survey import probe
from inmates.survey import survey


class Response(BytesIO):
    status = 200

    def __init__(self, body: bytes, url: str):
        super().__init__(body)
        self.url = url

    def geturl(self):
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def fake_urlopen(outcomes):
    def opener(request, timeout):
        outcome = outcomes[request.full_url]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
    return opener


def test_probe_classifies_responses(monkeypatch):
    outcomes = {
        'http://a/roster': Response(b'<html>roster</html>', 'http://a/roster'),
        'http://b/NewWorld.InmateInquiry/x': Response(b'<html>', 'http://b/NewWorld.InmateInquiry/x'),
        'http://c/old': Response(b'<html>', 'https://new.c/jail'),
        'http://g/': Response(b'<html>', 'https://www.g/'),
        'http://d/': HTTPError('http://d/', 403, 'Forbidden', {}, None),
        'http://e/': HTTPError('http://e/', 404, 'Not Found', {}, None),
        'http://f/': URLError('timed out'),
    }
    monkeypatch.setattr(module, 'urlopen', fake_urlopen(outcomes))

    assert probe('http://a/roster').status == 'ok'
    assert probe('http://b/NewWorld.InmateInquiry/x').platform == 'newworld'
    moved = probe('http://c/old')
    assert (moved.status, moved.final_url) == ('moved', 'https://new.c/jail')
    assert probe('http://g/').status == 'ok'
    assert probe('http://d/').status == 'blocked'
    assert probe('http://e/').status == 'http 404'
    assert probe('http://f/').status == 'unreachable'
    assert probe('').status == 'none'


def test_detect_platform_from_body_as_well_as_url():
    assert detect_platform('http://x/jail', '<a href="/ArchonixXJailPublic/">') == 'archonix'
    assert detect_platform('http://inmates.bluhorse.com/default.aspx?ID=W') == 'bluhorse'
    assert detect_platform('http://x/plain') is None


def test_read_index_folds_unnamed_columns_into_notes(tmp_path):
    path = tmp_path / 'inmates.csv'
    path.write_text(
        'IL County,Website,Roster Link,PDF,Notes,\n'
        'Crawford County,,http://x,TRUE,PDF updates weekly,IT IS A WIX SITE\n'
        'Cass County,,,,,\n'
    )
    rows = read_index(path)
    assert rows[0]['Notes'] == 'PDF updates weekly; IT IS A WIX SITE'
    assert rows[1]['Notes'] == ''
    assert set(rows[0]) == set(COLUMNS)


def test_survey_stamps_status_and_round_trips(tmp_path, monkeypatch):
    outcomes = {'http://x/NewWorld.InmateInquiry/': Response(b'', 'http://x/NewWorld.InmateInquiry/')}
    monkeypatch.setattr(module, 'urlopen', fake_urlopen(outcomes))
    rows = [
        {'IL County': 'Macon County', 'Roster Link': 'http://x/NewWorld.InmateInquiry/', 'Notes': ''},
        {'IL County': 'Cass County', 'Roster Link': '', 'Notes': ''},
    ]
    survey(rows, today='2026-10-22')
    assert (rows[0]['Status'], rows[0]['Checked'], rows[0]['Platform']) == ('ok', '2026-10-22', 'newworld')
    assert (rows[1]['Status'], rows[1]['Checked']) == ('none', '')

    path = tmp_path / 'inmates.csv'
    write_index(path, rows)
    assert path.read_text().splitlines()[0] == ','.join(COLUMNS)
    assert read_index(path)[0]['Platform'] == 'newworld'
