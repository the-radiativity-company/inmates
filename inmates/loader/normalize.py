"""Normalizers: roster JSON record -> Person with Bookings and Charges.

Each roster prints something different. A normalizer fills whatever normalized
fields the roster supports and leaves the rest None; the raw record always
travels along so it can be re-read later. Normalizers are keyed by platform
(one vendor's software, shared by many counties) or, failing that, by county.
"""
import json
import re

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

    def finish(self, derive_hold: bool = True) -> 'Booking':
        """derives what the county did not say outright; derive_hold=False keeps a None hold_type as meaning no hold"""
        if self.hold_type is None and derive_hold:
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


def normalize_mmmicro(record: dict) -> Person:
    """
    a details-page record from the M&M Micro spider. 'Class' is the custody
    classification (DETAINED BY JUDGE, DETAIN FOR HEARING 48 HRS, NO BOND,
    DETAINABLE OFFENSE, CONVICTED FELON, HOLD FOR OTHER AGENCY); CONVICTED
    reads as serving a sentence and the rest feed hold detection. Bond is a
    bare number per charge, 0 meaning none.
    """
    name = clean_text(record.get('Name'))
    race, _, sex = (clean_text(record.get('Race/Sex')) or '').partition('/')
    custody_class = (clean_text(record.get('Class')) or '').upper()
    entries = record.get('Charges') or []
    charges = [charge_from_text(c.get('TCA Description')) for c in entries if clean_text(c.get('TCA Description'))]
    bonds = [parse_money(c.get('Bond')) for c in entries]
    court_dates = [iso_datetime(c.get('Court Date')) for c in entries]
    booking = Booking(
        booking_date=iso_datetime(record.get('Intake Date')),
        next_court_date=max(filter(None, court_dates), default=None),
        detention_status='sentenced' if 'CONVICTED' in custody_class else None,
        financial_hold=max((b for b in bonds if b), default=0.0 if bonds else None),
        hold_type=hold_type_for(custody_class, *(c.description for c in charges)),
        charges=charges,
        raw=record,
    ).finish()
    return Person(
        county_person_key=clean_text(record.get('Id')) or person_key(name),
        name=name,
        age=parse_int(record.get('Age')),
        sex=normalize_sex(sex),
        race=normalize_race(race),
        bookings=[booking],
        raw=record,
    )


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


# every sheriff labels hold_reasons entries their own way ("Charge (ON VIEW):", "New Offense:",
# "Charge/Arrest:", "Warrant-McDonough:", "Sentencing Order:", "Additional Hold for Parole", ...),
# so the parser keys on what the text contains rather than on the label
ZUERCHER_STATUTE = re.compile(r'(\d{3}[\s-]+(?:ILCS[\s-]+)?[\d.]+/[\w.\-()]+)')
ZUERCHER_STATUS = re.compile(r'\s*\((?P<status>Pending|Dismissed|Disposed|Guilty|Sentenced)\)\s*$', re.I)
ZUERCHER_DOCKET = re.compile(r'warrant\s+(?P<docket>[A-Z0-9]*\d[A-Z0-9-]*)\b', re.I)
ZUERCHER_ISSUER = re.compile(r'issued by\s*(?P<agency>[^;(]*)', re.I)
ZUERCHER_STATE = re.compile(r',\s*([A-Z]{2})\b\s*\)?\s*$')
DOLLARS = re.compile(r'\$\s*([\d,]+(?:\.\d+)?)')


def dollars(text) -> Optional[float]:
    """the $ figure in '10%, $40000.00' (parse_money would take the 10)"""
    match = DOLLARS.search(text or '')
    return float(match.group(1).replace(',', '')) if match else None


def zuercher_hold_reasons(text) -> List[dict]:
    """splits the portal's hold_reasons string into one dict per charge, warrant, sentence, or hold

    'Charge (ON VIEW): 720 ILCS 5/12-3.2 - DOMESTIC BATTERY (Pending); Arrest Date 10/13/2026; Bond - No Bond, $0.00; Set By Judge;'
    -> {'kind': 'charge', 'label': 'Charge (ON VIEW)', 'statute': '720 ILCS 5/12-3.2', 'text': 'DOMESTIC BATTERY',
        'status': 'Pending', 'arrest_date': '10/13/2026', 'bond': 'No Bond, $0.00'}
    """
    reasons = []
    for entry in re.split(r'<br\s*/?>', text or ''):
        parts = [p.strip() for p in entry.split(';') if p.strip()]
        if not parts:
            continue
        head = parts[0]
        label, _, body = head.partition(':') if ':' in head else ('', '', head)
        label, body = label.strip(), body.strip()
        reason = {'label': label or None}
        status = ZUERCHER_STATUS.search(body)
        if status:
            reason['status'] = status.group('status')
            body = ZUERCHER_STATUS.sub('', body)
        statute = ZUERCHER_STATUTE.search(body)
        haystack = f'{label} {body}'.upper()
        if 'SENTENC' in haystack or 'SERVING' in haystack:
            reason['kind'] = 'sentence'
        elif 'WARRANT' in haystack:
            reason['kind'] = 'warrant'
        elif statute or 'CHARGE' in haystack or 'OFFENSE' in haystack:
            reason['kind'] = 'charge'
        else:
            reason['kind'] = 'hold'
        if statute:
            reason['statute'] = re.sub(r'^(\d{3})[\s-]+(?!ILCS)', r'\1 ILCS ', statute.group(1).replace('-', ' ', 1) if ' ILCS' not in statute.group(1) else statute.group(1))
            after = body[statute.end():]
            description = re.split(r'\s*[-~]\s*', after, maxsplit=1)[-1] if after.strip() else ''
            reason['text'] = clean_text(description.strip(' -~()')) or None
        else:
            reason['text'] = clean_text(re.sub(r'\(Converted Statute[^)]*\)', '', body).strip(' -~()')) or clean_text(label)
        if reason['kind'] == 'warrant':
            docket = ZUERCHER_DOCKET.search(head)
            issuer = ZUERCHER_ISSUER.search(head)
            reason['docket'] = docket.group('docket') if docket else None
            reason['agency'] = clean_text(issuer.group('agency')) if issuer else None
        for part in parts[1:]:
            if part.lower().startswith('arrest date'):
                reason['arrest_date'] = part[len('arrest date'):].strip()
            elif part.lower().startswith('bond -'):
                reason['bond'] = part[len('bond -'):].strip()
        reasons.append(reason)
    return reasons


def zuercher_out_of_state(agency: Optional[str]) -> bool:
    """'Scott CO. IA, IA' -> True; 'Rock Island CO. IL, IL' and 'KNOX COUNTY' -> False"""
    match = ZUERCHER_STATE.search(agency or '')
    return bool(match) and match.group(1) != 'IL'


def normalize_zuercher(record: dict) -> Person:
    """a record from the CentralSquare/Zuercher portal API; 'dob' is an age on most installs, a date on some"""
    name = clean_text(record.get('name'))
    arrest_date = iso_date(record.get('arrest_date'))
    reasons = zuercher_hold_reasons(record.get('hold_reasons'))
    charges = [
        Charge(description=r.get('text'), statute=r.get('statute'), docket_number=r.get('docket'),
               offense_date=iso_date(r.get('arrest_date')))
        for r in reasons if r['kind'] in ('charge', 'warrant')
    ]
    bonds = [dollars(r.get('bond')) for r in reasons]
    held_for = clean_text(record.get('held_for_agency'))
    out_of_state = any(zuercher_out_of_state(r.get('agency')) for r in reasons if r['kind'] == 'warrant')
    sentenced = reasons and all(r['kind'] == 'sentence' for r in reasons)
    # an arrest on a local warrant is ordinary pretrial detention, not a hold for someone else,
    # so only the held-for agency, out-of-state warrants, and the entry text itself make a hold
    hold_texts = [r.get('text') or '' for r in reasons if r['kind'] in ('charge', 'hold')] + [r.get('label') or '' for r in reasons if r['kind'] == 'hold']
    booking = Booking(
        booking_date=arrest_date,
        release_date=iso_date(record.get('release_date')),
        detention_status='sentenced' if sentenced and not record.get('release_date') else None,
        arresting_agency=held_for,
        financial_hold=max((b for b in bonds if b), default=0.0 if bonds else None),
        hold_type='out_of_state' if out_of_state else hold_type_for(held_for, *hold_texts),
        charges=charges,
        raw=record,
    ).finish(derive_hold=False)
    dob = record.get('dob')
    return Person(
        county_person_key=person_key(name, arrest_date),
        name=name,
        dob=iso_date(dob) if isinstance(dob, str) and '-' in dob else None,
        age=parse_int(dob) if not (isinstance(dob, str) and '-' in dob) else None,
        sex=normalize_sex(record.get('sex')),
        race=normalize_race(record.get('race')),
        facility=clean_text(record.get('cell_block')),
        bookings=[booking],
        raw=record,
    )


def normalize_recordssearch(record: dict) -> Person:
    """a person from the Tyler Corrections Records Search API: arrests each carry charges, bonds carry amounts"""
    name = clean_text((record.get('name') or {}).get('fullName'))
    arrests = sorted(record.get('arrests') or [], key=lambda a: a.get('arrestDate') or '')
    charges = [
        Charge(
            description=clean_text((c.get('statute') or {}).get('description')),
            offense_class=clean_text((c.get('statute') or {}).get('degree')),
            docket_number=clean_text(c.get('caseNumber')),
            offense_date=iso_datetime(arrest.get('arrestDate')),
        )
        for arrest in arrests for c in arrest.get('charges') or []
    ]
    bonds = record.get('bonds') or []
    amounts = [b.get('amount') for b in bonds if isinstance(b.get('amount'), (int, float))]
    latest = arrests[-1] if arrests else {}
    booking = Booking(
        booking_date=iso_datetime(latest.get('arrestDate')),
        detention_status='released' if record.get('IsReleased') else None,
        arresting_agency=clean_text(latest.get('arrestingAgency')),
        financial_hold=max(amounts, default=0.0 if bonds else None),
        charges=charges,
        raw=record,
    ).finish()
    return Person(
        county_person_key=clean_text(record.get('soNumber')) or clean_text(record.get('id')) or person_key(name),
        name=name,
        age=parse_int(record.get('age')),
        sex=normalize_sex(record.get('gender')),
        race=normalize_race(record.get('race')),
        bookings=[booking],
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


def normalize_tazewell(record: dict) -> Person:
    """one row of the sheriff's in-custody table: a person with one charge and no bond"""
    last = clean_text(record.get('LastName'))
    first = ' '.join(filter(None, (clean_text(record.get('FirstName')), clean_text(record.get('MiddleInit')))))
    name = ', '.join(filter(None, (last, first))) or None
    booked = ' '.join(filter(None, (clean_text(record.get('BookDate')), clean_text(record.get('BookTime')))))
    booking = Booking(
        booking_date=iso_datetime(booked),
        arresting_agency=clean_text(record.get('Agency')),
        charges=[charge_from_text(record['Charge'])] if clean_text(record.get('Charge')) else [],
        raw=record,
    ).finish()
    return Person(
        county_person_key=clean_text(record.get('DetaineeID')) or person_key(name),
        name=name,
        age=parse_int(record.get('Age')),
        sex=normalize_sex(record.get('Sex')),
        race=normalize_race(record.get('Race')),
        bookings=[booking],
        raw=record,
    )


def normalize_lawrence(record: dict) -> Person:
    """an article from the sheriff's in-custody page; 'TIME SERVER' as the only charge means a sentence being served"""
    name = clean_text(record.get('Name'))
    race, _, sex = (clean_text(record.get('Race/Sex')) or '').partition('/')
    intake = record.get('Intake Date')
    entries = record.get('Charges') or []
    charges = [charge_from_text(c.get('Charge')) for c in entries if clean_text(c.get('Charge'))]
    bonds = [parse_money(c.get('Bond')) for c in entries]
    serving = bool(charges) and all('TIME SERVE' in (c.description or '').upper() for c in charges)
    booking = Booking(
        booking_date=iso_datetime(intake),
        release_date=iso_datetime(record.get('Release Date')),
        detention_status='sentenced' if serving and not record.get('Release Date') else None,
        arresting_agency=clean_text(record.get('Arrested By Department')),
        financial_hold=max((b for b in bonds if b), default=0.0 if bonds else None),
        charges=charges,
        raw=record,
    ).finish()
    return Person(
        county_person_key=person_key(name, iso_date(intake)),
        name=name,
        age=parse_int(record.get('Age')),
        sex=normalize_sex(sex),
        race=normalize_race(race),
        bookings=[booking],
        raw=record,
    )


def normalize_randolph(record: dict) -> Person:
    """one table of the sheriff's listing: a name and its charges, each with bond text or an amount; no dates or demographics"""
    name = re.sub(r',\s*', ', ', clean_text(record.get('Name')) or '') or None
    entries = record.get('Charges') or []
    charges = [charge_from_text(c.get('Charge')) for c in entries if clean_text(c.get('Charge'))]
    bonds = [parse_money(c.get('Bond')) for c in entries]
    booking = Booking(
        financial_hold=max((b for b in bonds if b), default=0.0 if bonds else None),
        charges=charges,
        raw=record,
    ).finish()
    return Person(county_person_key=person_key(name), name=name, bookings=[booking], raw=record)


def normalize_generic(record: dict) -> Person:
    """for a county with no normalizer yet: find a name, keep everything raw"""
    fields = colonless(record)
    name_key = next((k for k in fields if 'name' in k.lower()), None)
    name = clean_text(fields.get(name_key)) if name_key else None
    return Person(county_person_key=person_key(name or json.dumps(record, sort_keys=True)), name=name, raw=record)


NORMALIZERS: Dict[str, Callable[[dict], Person]] = {
    'adams': normalize_adams,
    'lawrence': normalize_lawrence,
    'mmmicro': normalize_mmmicro,
    'newworld': normalize_newworld,
    'randolph': normalize_randolph,
    'recordssearch': normalize_recordssearch,
    'stclair': normalize_stclair,
    'tazewell': normalize_tazewell,
    'zuercher': normalize_zuercher,
}


def normalize(county: str, record: dict, platform: Optional[str] = None) -> Person:
    """the platform's normalizer when there is one, else the county's, else a name-only fallback"""
    normalizer = NORMALIZERS.get(platform or '') or NORMALIZERS.get(county, normalize_generic)
    return normalizer(record)
