"""The roster index: which counties have spiders and where their rosters live."""
from csv import DictReader
from csv import DictWriter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict
from typing import Iterable
from typing import List

from inmates.utils import get_modules_from


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROSTER_INDEX = PROJECT_ROOT / 'inmates.csv'
COLUMNS = ['IL County', 'Website', 'Roster Link', 'PDF', 'Platform', 'Status', 'Checked', 'Notes']


def read_index(path: Path = ROSTER_INDEX) -> List[Dict[str, str]]:
    """reads the roster index, folding any unnamed trailing columns into Notes"""
    with Path(path).open(newline='') as fh:
        rows = []
        for raw in DictReader(fh):
            row = {column: (raw.get(column) or '').strip() for column in COLUMNS}
            overflow = [str(v).strip() for k, v in raw.items() if k not in COLUMNS and v]
            row['Notes'] = '; '.join(part for part in [row['Notes'], *overflow] if part)
            rows.append(row)
        return rows


def write_index(path: Path, rows: Iterable[Dict[str, str]]) -> None:
    with Path(path).open('w', newline='') as fh:
        writer = DictWriter(fh, fieldnames=COLUMNS, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, '') for column in COLUMNS})


def county_slug(cell: str) -> str:
    """'St. Clair County' -> 'stclair', matching spider module names"""
    return cell.replace(' County', '').replace('. ', '').replace(' ', '').lower()


def spider_names() -> list:
    return sorted(path.stem for path in get_modules_from('inmates.scraper.spiders'))


@dataclass(frozen=True)
class Roster:
    county: str    # slug, e.g. 'stclair'; names the output file and the database rows
    url: str       # Roster Link from the index
    spider: str    # the platform spider when the index names a known Platform, else the county's own
    platform: str  # Platform column, possibly ''


def rosters(index: Path = ROSTER_INDEX) -> List[Roster]:
    """every county in the index that has a roster link and a spider able to read it"""
    names = spider_names()
    found = []
    for row in read_index(index):
        url, platform = row['Roster Link'], row['Platform']
        slug = county_slug(row['IL County'])
        spider = platform if platform in names else slug if slug in names else None
        if url and spider:
            found.append(Roster(slug, url, spider, platform))
    return found


def roster_names() -> List[str]:
    return [roster.county for roster in rosters()]


def roster_urls() -> Dict[str, str]:
    return {roster.county: roster.url for roster in rosters()}


def roster_platforms() -> Dict[str, str]:
    return {roster.county: roster.platform for roster in rosters()}
