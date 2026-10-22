"""Probes every roster link in the index and records what answered."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from typing import Dict
from typing import List
from typing import Optional
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request
from urllib.request import urlopen



USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
MAX_BODY = 256 * 1024

# substrings of a URL or page body that identify the vendor behind a roster
PLATFORM_HINTS = (
    ('newworld.inmateinquiry', 'newworld'),
    ('archonixxjail', 'archonix'),
    ('bluhorse', 'bluhorse'),
    ('jailtracker', 'jailtracker'),
    ('zuercherportal', 'zuercher'),
    ('/p2c/', 'zuercher'),
    ('inmateinquiry', 'newworld'),
    ('smartcop', 'smartcop'),
    ('vinelink', 'vinelink'),
)


@dataclass
class Probe:
    status: str
    code: Optional[int] = None
    final_url: Optional[str] = None
    platform: Optional[str] = None


def detect_platform(*texts: Optional[str]) -> Optional[str]:
    haystack = ' '.join(t for t in texts if t).lower()
    for hint, platform in PLATFORM_HINTS:
        if hint in haystack:
            return platform
    return None


def host(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix('www.')


def probe(url: Optional[str], timeout: float = 20) -> Probe:
    """fetches `url` with a browser user agent and classifies the answer"""
    if not url:
        return Probe('none')
    request = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': '*/*'})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(MAX_BODY).decode('utf-8', errors='replace')
            final_url = response.geturl()
            moved = host(final_url) != host(url)
            status = 'moved' if moved else 'ok'
            return Probe(status, response.status, final_url, detect_platform(url, final_url, body))
    except HTTPError as error:
        status = 'blocked' if error.code in (401, 403) else f'http {error.code}'
        return Probe(status, error.code, platform=detect_platform(url))
    except (URLError, TimeoutError, OSError, ValueError):
        return Probe('unreachable', platform=detect_platform(url))


def survey(rows: List[Dict[str, str]], timeout: float = 20, workers: int = 8, today: Optional[str] = None) -> List[Probe]:
    """probes each row's Roster Link in parallel and stamps Status, Checked, and Platform in place"""
    today = today or date.today().isoformat()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        probes = list(pool.map(lambda row: probe(row.get('Roster Link'), timeout), rows))
    for row, result in zip(rows, probes):
        row['Status'] = result.status
        row['Checked'] = today if result.status != 'none' else ''
        if result.platform and not row.get('Platform'):
            row['Platform'] = result.platform
    return probes
