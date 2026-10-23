"""The current-custody database: who each county lists right now, upserted per scrape."""
import json
import sqlite3

from dataclasses import dataclass
from pathlib import Path
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional

from inmates.loader.normalize import normalize
from inmates.loader.normalize import Person


SCHEMA = """
CREATE TABLE IF NOT EXISTS scrape_run (
    id            INTEGER PRIMARY KEY,
    county        TEXT NOT NULL,
    scraped_at    TEXT NOT NULL,
    record_count  INTEGER NOT NULL,
    status        TEXT NOT NULL,            -- ok | empty | missing
    UNIQUE (county, scraped_at)
);

CREATE TABLE IF NOT EXISTS person (
    id                INTEGER PRIMARY KEY,
    county            TEXT NOT NULL,
    county_person_key TEXT NOT NULL,
    name              TEXT,
    dob               TEXT,
    age               INTEGER,
    sex               TEXT,
    race              TEXT,
    facility          TEXT,
    in_custody        INTEGER NOT NULL DEFAULT 1,
    first_seen        TEXT NOT NULL,
    last_seen         TEXT NOT NULL,
    source_url        TEXT,
    raw               TEXT NOT NULL,        -- the county's record as scraped, JSON
    UNIQUE (county, county_person_key)
);
CREATE INDEX IF NOT EXISTS person_custody ON person (county, in_custody);

CREATE TABLE IF NOT EXISTS booking (
    id               INTEGER PRIMARY KEY,
    person_id        INTEGER NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    booking_number   TEXT,
    booking_date     TEXT,
    release_date     TEXT,
    detention_status TEXT,                  -- detained | hold | sentenced | released
    hold_type        TEXT,                  -- federal | doc | out_of_state | warrant | hold
    next_court_date  TEXT,
    arresting_agency TEXT,
    financial_hold   REAL,                  -- legacy bond figure; null post-2023 for most counties
    raw              TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS booking_person ON booking (person_id);

CREATE TABLE IF NOT EXISTS charge (
    id            INTEGER PRIMARY KEY,
    booking_id    INTEGER NOT NULL REFERENCES booking(id) ON DELETE CASCADE,
    description   TEXT,
    statute       TEXT,
    offense_class TEXT,
    detainable    INTEGER,
    docket_number TEXT,
    offense_date  TEXT
);
CREATE INDEX IF NOT EXISTS charge_booking ON charge (booking_id);

-- One row per person in custody per open booking (or one row with null booking fields
-- for counties that publish no booking detail).
CREATE VIEW IF NOT EXISTS current_custody AS
SELECT p.county, p.name, p.dob, p.age, p.sex, p.race, p.facility,
       p.first_seen, p.last_seen,
       CAST(julianday(p.last_seen) - julianday(p.first_seen) AS INTEGER) AS days_observed,
       b.booking_number, b.booking_date, b.detention_status, b.hold_type,
       b.next_court_date, b.arresting_agency, b.financial_hold,
       (SELECT group_concat(COALESCE(c.statute || ' ', '') || COALESCE(c.description, ''), '; ')
          FROM charge c WHERE c.booking_id = b.id) AS charges
  FROM person p
  LEFT JOIN booking b ON b.person_id = p.id AND b.release_date IS NULL
 WHERE p.in_custody = 1;
"""


@dataclass
class RunResult:
    county: str
    status: str           # ok | empty | missing | duplicate
    record_count: int
    loaded: int = 0
    released: int = 0


def connect(path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.execute('PRAGMA foreign_keys = ON')
    conn.executescript(SCHEMA)
    return conn


def still_held(person: Person) -> bool:
    """a roster can list someone it has just released (McHenry keeps them a day or two); they are not in custody"""
    return not person.bookings or any(b.release_date is None for b in person.bookings)


def upsert_person(conn: sqlite3.Connection, county: str, person: Person, scraped_at: str, source_url: Optional[str]) -> int:
    row = conn.execute(
        """
        INSERT INTO person (county, county_person_key, name, dob, age, sex, race, facility,
                            in_custody, first_seen, last_seen, source_url, raw)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (county, county_person_key) DO UPDATE SET
            name       = excluded.name,
            dob        = COALESCE(excluded.dob, person.dob),
            age        = COALESCE(excluded.age, person.age),
            sex        = COALESCE(excluded.sex, person.sex),
            race       = COALESCE(excluded.race, person.race),
            facility   = excluded.facility,
            in_custody = excluded.in_custody,
            last_seen  = excluded.last_seen,
            source_url = excluded.source_url,
            raw        = excluded.raw
        RETURNING id
        """,
        (county, person.county_person_key, person.name, person.dob, person.age, person.sex,
         person.race, person.facility, int(still_held(person)), scraped_at, scraped_at, source_url, person.as_json()),
    ).fetchone()
    return row[0]


def replace_bookings(conn: sqlite3.Connection, person_id: int, person: Person) -> None:
    conn.execute('DELETE FROM booking WHERE person_id = ?', (person_id,))
    for booking in person.bookings:
        booking_id = conn.execute(
            """
            INSERT INTO booking (person_id, booking_number, booking_date, release_date, detention_status,
                                 hold_type, next_court_date, arresting_agency, financial_hold, raw)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (person_id, booking.booking_number, booking.booking_date, booking.release_date,
             booking.detention_status, booking.hold_type, booking.next_court_date,
             booking.arresting_agency, booking.financial_hold, json.dumps(booking.raw, sort_keys=True)),
        ).lastrowid
        conn.executemany(
            """
            INSERT INTO charge (booking_id, description, statute, offense_class, detainable, docket_number, offense_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [(booking_id, c.description, c.statute, c.offense_class, c.detainable, c.docket_number, c.offense_date)
             for c in booking.charges],
        )


def load_county(
    conn: sqlite3.Connection,
    county: str,
    records: Optional[List[dict]],
    scraped_at: str,
    source_url: Optional[str] = None,
    platform: Optional[str] = None,
) -> RunResult:
    """Loads one county's scrape. `records` None means the scrape produced no file.

    Only a successful, non-empty scrape marks absent people as no longer in custody;
    an empty or missing scrape is treated as a scraper failure, not a mass release.
    Someone the roster itself lists as released (every booking has a release date)
    is loaded, kept, and counted as released, but not as in custody.
    Loads must be applied in chronological order of scraped_at.
    """
    if records is None:
        status, records = 'missing', []
    else:
        status = 'ok' if records else 'empty'

    with conn:
        inserted = conn.execute(
            'INSERT OR IGNORE INTO scrape_run (county, scraped_at, record_count, status) VALUES (?, ?, ?, ?)',
            (county, scraped_at, len(records), status),
        ).rowcount
        if not inserted:
            return RunResult(county, 'duplicate', len(records))
        if status != 'ok':
            return RunResult(county, status, 0)

        released = 0
        for record in records:
            person = normalize(county, record, platform)
            person_id = upsert_person(conn, county, person, scraped_at, source_url)
            replace_bookings(conn, person_id, person)
            released += not still_held(person)

        released += conn.execute(
            'UPDATE person SET in_custody = 0 WHERE county = ? AND in_custody = 1 AND last_seen < ?',
            (county, scraped_at),
        ).rowcount

    return RunResult(county, status, len(records), loaded=len(records), released=released)


def read_records(path: Path) -> Optional[List[dict]]:
    if not path.exists():
        return None
    text = path.read_text().strip()
    return json.loads(text) if text else []


def load_directory(
    conn: sqlite3.Connection,
    indir: Path,
    scraped_at: str,
    counties: Iterable[str],
    source_urls: Optional[Dict[str, str]] = None,
    platforms: Optional[Dict[str, str]] = None,
) -> List[RunResult]:
    source_urls, platforms = source_urls or {}, platforms or {}
    return [
        load_county(conn, county, read_records(indir / f'{county}.json'), scraped_at,
                    source_urls.get(county), platforms.get(county))
        for county in counties
    ]
