"""Tolerant parsers for the strings counties print on their rosters."""
import re

from datetime import date
from datetime import datetime
from html import unescape
from typing import Optional
from typing import Tuple


TAG_RE = re.compile(r'<[^>]+>')
WS_RE = re.compile(r'\s+')
STATUTE_RE = re.compile(r'^\s*(\d+\s+ILCS\s+[\d.]+/[\w.\-()]+)\s*(.*)$', re.I)
MONEY_RE = re.compile(r'-?\d[\d,]*(?:\.\d+)?')

DATETIME_FORMATS = (
    '%m/%d/%Y %I:%M %p',
    '%m/%d/%Y %H:%M',
    '%m/%d/%Y',
    '%m-%d-%Y - %I:%M %p',
    '%m-%d-%Y',
    '%A %B %d, %Y at %I:%M %p',
    '%A %B %d, %Y @ %I:%M %p',
    '%A %B %d, %Y',
    '%B %d, %Y',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%d',
)

HOLD_TYPES = (
    ('federal', ('FEDERAL', 'U.S. MARSHAL', 'US MARSHAL', 'USM ')),
    ('doc', ('DEPARTMENT OF CORRECTIONS', 'IDOC', 'PAROLE')),
    ('out_of_state', ('FUGITIVE', 'OUT OF STATE', 'EXTRADITION', 'OUT-OF-STATE')),
    ('warrant', ('WARRANT',)),
    ('hold', ('HOLD',)),
)


def clean_text(value) -> Optional[str]:
    """strips markup and collapses whitespace; empty becomes None"""
    if value is None:
        return None
    text = WS_RE.sub(' ', TAG_RE.sub(' ', unescape(str(value)))).strip()
    return text or None


def parse_datetime(value) -> Optional[datetime]:
    text = clean_text(value)
    if not text:
        return None
    text = re.sub(r'^Next Court:\s*', '', text, flags=re.I)
    text = text.split('(')[0]                           # "(423 days in custody)"
    text = re.split(r',\s*Room\b', text, flags=re.I)[0]  # ", Room 410, Status Conference"
    text = WS_RE.sub(' ', text).strip().rstrip('.').strip()
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def iso_datetime(value) -> Optional[str]:
    parsed = parse_datetime(value)
    return parsed.isoformat(sep=' ') if parsed else None


def iso_date(value) -> Optional[str]:
    parsed = parse_datetime(value)
    return parsed.date().isoformat() if parsed else None


def parse_money(value) -> Optional[float]:
    text = clean_text(value)
    if not text:
        return None
    match = MONEY_RE.search(text)
    return float(match.group().replace(',', '')) if match else None


def parse_int(value) -> Optional[int]:
    text = clean_text(value)
    if not text:
        return None
    digits = re.search(r'\d+', text)
    return int(digits.group()) if digits else None


def split_statute(value) -> Tuple[Optional[str], Optional[str]]:
    """'720 ILCS 5/9-1 FIRST DEGREE MURDER' -> ('720 ILCS 5/9-1', 'FIRST DEGREE MURDER')"""
    text = clean_text(value)
    if not text:
        return None, None
    match = STATUTE_RE.match(text)
    if not match:
        return None, text
    statute, description = match.groups()
    return WS_RE.sub(' ', statute).upper(), (description.strip() or None)


def hold_type_for(*texts) -> Optional[str]:
    haystack = ' '.join(clean_text(t) or '' for t in texts).upper()
    for hold_type, needles in HOLD_TYPES:
        if any(needle in haystack for needle in needles):
            return hold_type
    return None


def normalize_sex(value) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    first = text[0].upper()
    return first if first in ('M', 'F') else text.upper()


def normalize_race(value) -> Optional[str]:
    text = clean_text(value)
    return text.upper() if text else None


def person_key(*parts) -> str:
    """a stable key from whatever identifying parts a county gives us"""
    cleaned = [clean_text(p) or '' for p in parts]
    return '|'.join(cleaned).lower()


def colonless(record: dict) -> dict:
    """{'Name:': ...} -> {'Name': ...}; some rosters print the label with its colon"""
    return {str(k).rstrip(':').strip(): v for k, v in record.items()}


def today() -> date:
    return date.today()
