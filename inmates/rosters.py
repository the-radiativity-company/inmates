"""The roster index: which counties have spiders and where their rosters live."""
from csv import DictReader
from csv import DictWriter
from pathlib import Path
from typing import Dict
from typing import Iterable
from typing import List

from inmates.utils import build_dict
from inmates.utils import format_records
from inmates.utils import get_modules_from
from inmates.utils import produce_records


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


def roster_urls() -> dict:
    """maps each spider name to the roster URL recorded for its county in inmates.csv"""
    all_links = build_dict(
        format_records(
            produce_records(ROSTER_INDEX),
            ('IL County', county_slug),
            ('Roster Link', lambda cell: cell),
        )
    )
    return {name: all_links[name] for name in spider_names() if name in all_links}
