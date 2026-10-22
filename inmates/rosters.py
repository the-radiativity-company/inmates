"""The roster index: which counties have spiders and where their rosters live."""
from pathlib import Path

from inmates.utils import build_dict
from inmates.utils import format_records
from inmates.utils import get_modules_from
from inmates.utils import produce_records


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROSTER_INDEX = PROJECT_ROOT / 'inmates.csv'


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
