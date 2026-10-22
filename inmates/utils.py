from csv import DictReader
from os import walk
from os.path import join as joinpath
from pathlib import Path
from sys import exit
from sys import stdout
from typing import Any
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import Tuple


SKIPPED_FILENAME_FRAGMENTS = ('__main__.py', '__init__.py', 'cpython', '.pyc')


def all_files_in(directory) -> list:
    """returns absolute paths for all files below `directory`, irrespective of nesting"""
    found = []
    for root, _dirs, files in walk(directory, topdown=True):
        for name in files:
            if not any(fragment in name for fragment in SKIPPED_FILENAME_FRAGMENTS):
                found.append(joinpath(root, name))
    return found


def get_modules_from(package: str) -> set:
    """returns the source file paths that make up `package`, resolved relative to this package's parent"""
    package_root = Path(__file__).resolve().parent.parent
    return {Path(p) for p in all_files_in(package_root / package.replace('.', '/')) if p.endswith('.py')}


def not_none(iterable: Iterable) -> Iterator:
    yield from (item for item in iterable if item not in ('', None, [], (), {}))


def exit_proc(msg, code, file=stdout):
    print(msg, file=file)
    exit(code)


def read_file(filename: str) -> str:
    path = Path(filename)
    if not path.exists():
        raise FileNotFoundError(filename)
    return path.read_text().strip()


def format_records(
    records: Iterable[Dict[str, str]],
    *formatters: Tuple[str, Callable[[str], str]],
) -> Iterator[Dict[str, str]]:
    """yields a header row (values None) then one dict per record, with each column run through its formatter"""
    yield {header: None for header, _ in formatters}
    for record in records:
        yield {header: formatter(record.get(header)) for header, formatter in formatters}


def build_csv(formatted_records: Iterator[Dict[str, str]]) -> str:
    headers = ','.join(next(formatted_records))
    rows = [','.join(str(v) for v in r.values()) for r in formatted_records]
    return ',\n'.join([headers.rjust(32), *rows])


def build_dict(formatted_records: Iterator[Dict[str, str]]) -> dict:
    keys = list(next(formatted_records).keys())
    if len(keys) != 2:
        raise ValueError('Exactly two keys required.')
    k1, k2 = keys
    return {record[k1]: record[k2] for record in formatted_records}


def produce_records(csvfile: str) -> Iterator[Dict[str, str]]:
    with Path(csvfile).open(newline='') as fh:
        yield from DictReader(fh)


def handle_csv(
    csvfile: str,
    *columns_and_formatters: Tuple[str, Callable[..., Any]],
) -> str:
    with Path(csvfile).open(newline='') as fh:
        reader = DictReader(fh)
        headers = reader.fieldnames or []
        for col, _ in columns_and_formatters:
            if col not in headers:
                listing = ''.join(f'\n\t\t* {h}' for h in not_none(headers))
                exit_proc(f'\n\t❌ "{col}" not a valid column name in "{csvfile}": {listing}\n', 187)
        records = list(reader)
    return build_csv(format_records(records, *columns_and_formatters))
