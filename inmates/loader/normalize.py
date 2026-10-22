"""Normalizers: roster JSON record -> Person with Bookings and Charges.

Each roster prints something different. A normalizer fills whatever normalized
fields the roster supports and leaves the rest None; the raw record always
travels along so it can be re-read later. Normalizers are keyed by platform
(one vendor's software, shared by many counties) or, failing that, by county.
"""
import json

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional

from inmates.loader.parse import clean_text
from inmates.loader.parse import colonless
from inmates.loader.parse import hold_type_for
from inmates.loader.parse import iso_date
from inmates.loader.parse import iso_datetime
from inmates.loader.parse import normalize_race
from inmates.loader.parse import normalize_sex
from inmates.loader.parse import parse_int
from inmates.loader.parse import parse_money
from inmates.loader.parse import person_key
from inmates.loader.parse import split_statute


@dataclass
class Charge:
    description: Optional[str]
    statute: Optional[str] = None
    offense_class: Optional[str] = None
    detainable: Optional[bool] = None
    docket_number: Optional[str] = None
    offense_date: Optional[str] = None


@dataclass
class Booking:
    booking_number: Optional[str] = None
    booking_date: Optional[str] = None
    release_date: Optional[str] = None
    detention_status: Optional[str] = None
    hold_type: Optional[str] = None
    next_court_date: Optional[str] = None
    arresting_agency: Optional[str] = None
    financial_hold: Optional[float] = None
    charges: List[Charge] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    def finish(self) -> 'Booking':
        """derives what the county did not say outright"""
        if self.hold_type is None:
            self.hold_type = hold_type_for(*(c.description for c in self.charges), *(c.docket_number for c in self.charges))
        if self.detention_status is None:
            if self.release_date:
                self.detention_status = 'released'
            elif self.hold_type:
                self.detention_status = 'hold'
            else:
                self.detention_status = 'detained'
        return self


@dataclass
class Person:
    county_person_key: str
    name: Optional[str]
    dob: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    race: Optional[str] = None
    facility: Optional[str] = None
    bookings: List[Booking] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    def as_json(self) -> str:
        return json.dumps(self.raw, sort_keys=True)


def charge_from_text(text) -> Charge:
    statute, description = split_statute(text)
    return Charge(description=description or clean_text(text), statute=statute)


# --- counties -----------------------------------------------------------------

def normalize_adams(record: dict) -> Person:
    name = clean_text(record.get('name') or record.get('Name'))
    return Person(county_person_key=person_key(name), name=name, raw=record)


def normalize_newworld(record: dict) -> Person:
    """a detail-page record from the NewWorld InmateInquiry spider"""
    name = clean_text(record.get('Name'))
    key = clean_text(record.get('Subject Number')) or clean_text(record.get('Detail Id')) or person_key(name)
    bookings = []
    for raw_booking in record.get('Bookings') or []:
        charges = [
            Charge(
                description=clean_text(c.get('Charge Description')),
                offense_class=clean_text(c.get('Crime Class')),
                docket_number=clean_text(c.get('Docket Number')),
                offense_date=iso_datetime(c.get('Offense Date')),
            )
            for c in raw_booking.get('Charges') or []
        ]
        court_dates = [iso_datetime(c.get('Court Date')) for c in raw_booking.get('Court Dates') or []]
        prisoner_type = (clean_text(raw_booking.get('Prisoner Type')) or '').upper()
        bookings.append(Booking(
            booking_number=clean_text(raw_booking.get('Booking Number')),
            booking_date=iso_datetime(raw_booking.get('Booking Date')),
            release_date=iso_datetime(raw_booking.get('Release Date')),
            next_court_date=max(filter(None, court_dates), default=None),
            detention_status='sentenced' if 'SENTENCED' in prisoner_type and not raw_booking.get('Release Date') else None,
            arresting_agency=clean_text(raw_booking.get('Booking Origin')),
            financial_hold=parse_money(raw_booking.get('Total Bond Amount')),
            hold_type=hold_type_for(prisoner_type, *(c.description for c in charges), *(c.docket_number for c in charges)),
            charges=charges,
            raw=raw_booking,
        ).finish())
    open_bookings = [b for b in bookings if b.release_date is None]
    facility = clean_text(open_bookings[0].raw.get('Housing Facility')) if open_bookings else None
    return Person(
        county_person_key=key,
        name=name,
        age=parse_int(record.get('Age')),
        sex=normalize_sex(record.get('Gender')),
        race=normalize_race(record.get('Race')),
        facility=facility,
        bookings=bookings,
        raw=record,
    )


def normalize_stclair(record: dict) -> Person:
    fields = colonless(record)
    name = clean_text(fields.get('Name'))
    dob = iso_date(fields.get('DOB'))
    booking = Booking(
        booking_number=clean_text(fields.get('Booking Number')),
        booking_date=iso_datetime(fields.get('Booking Date')),
        next_court_date=iso_datetime(fields.get('Next Court Date')),
        financial_hold=parse_money(fields.get('Bond Amount')),
        hold_type=hold_type_for(fields.get('Bond Details'), fields.get('Booking Type')),
        charges=[charge_from_text(c) for c in fields.get('Charges') or []],
        raw=record,
    ).finish()
    return Person(
        county_person_key=person_key(name, dob),
        name=name,
        dob=dob,
        age=parse_int(fields.get('Age')),
        sex=normalize_sex(fields.get('Gender')),
        race=normalize_race(fields.get('Race')),
        bookings=[booking],
        raw=record,
    )


def normalize_generic(record: dict) -> Person:
    """for a county with no normalizer yet: find a name, keep everything raw"""
    fields = colonless(record)
    name_key = next((k for k in fields if 'name' in k.lower()), None)
    name = clean_text(fields.get(name_key)) if name_key else None
    return Person(county_person_key=person_key(name or json.dumps(record, sort_keys=True)), name=name, raw=record)


NORMALIZERS: Dict[str, Callable[[dict], Person]] = {
    'adams': normalize_adams,
    'newworld': normalize_newworld,
    'stclair': normalize_stclair,
}


def normalize(county: str, record: dict, platform: Optional[str] = None) -> Person:
    """the platform's normalizer when there is one, else the county's, else a name-only fallback"""
    normalizer = NORMALIZERS.get(platform or '') or NORMALIZERS.get(county, normalize_generic)
    return normalizer(record)
