from csv import DictReader
from functools import reduce
from hashlib import sha256
from importlib import import_module
from os import walk
from os.path import join as joinpath
from sys import exit
from sys import stdout
from pathlib import Path
from scrapy.crawler import Crawler
from scrapy.http import Request
from scrapy.settings import Settings
from typing import Any
from typing import Callable
from typing import Generator
from typing import Iterable
from typing import Tuple

from functools import partial
from operator import methodcaller
from oslash.either import Left
from oslash.either import Either
from oslash.either import Right
from oslash.util import compose
from pathlib import Path
from pprint import pprint
from sys import argv
from toolz.curried import map
from typing import Dict
from typing import List





def all_files_in(directory):
    """returns a list of absolute file paths for all files below `directory` irrespective of nesting"""
    all_files_and_directories_below = []
    for root, dirs, files, in walk(directory, topdown=True):
        for name in files:
            if not any(fragment in name for fragment in ['__main__.py', '__init__.py', 'cpython']):
                all_files_and_directories_below.append(joinpath(root, name))
    return all_files_and_directories_below


def get_modules_from(package: str):
    return set(Path(spider) for spider in all_files_in(package.replace('.', '/')))


def not_none(iterable: Iterable) -> Iterable:
    for item in filter(lambda item: item not in ['', None, [], (), {}], iterable):
        yield item


def exit_proc(msg, code, file=stdout):
    print(msg, file=file); exit(code)


def handle_csv(
    file: str,
    column1_name_and_formatter: Tuple[str, Callable[..., Any]],
    column2_name_and_formatter: Tuple[str, Callable[..., Any]],
) -> Generator[Tuple[str, str], None, None]:
    """
    For a given .csv file, a projection of row values under the two given columns are formatted and selected.
    For each column chosed, this function produces a tuple of all row values under said column.

    e.g. example.csv

    Names,Email,Lucky Number
    Chidinma,chidinma@chidinma.com,1
    Rosa,rosa@rosa.com,8
    Maxwell,maxwell@maxwell.com,7

    handled = handle_csv('example.csv', ('Names', lambda name: name.lower()), ('Number', lambda num: int(num) + 10))
    list(handled)
        => [('Names', 'Number'), ('chidinma', '11'), ('rosa', '18'), ('maxwell', '17')]
    """
    column1, c1formatter = column1_name_and_formatter
    column2, c2formatter = column2_name_and_formatter
    if not column1:
        raise ValueError('The first column must be specified.')
    with open(file) as csvfile:
        reader = DictReader(csvfile)
        header = reader.fieldnames
        if column2:
            if column2 not in header:
                predicate, init = lambda a, b: f"{a}\n\t\t* {b}", '\n\t\t'
                exit_proc(f'\n\t❌ "{column2}" not a valid column name in "{csvfile.name}": {reduce(predicate, not_none(header), init)}\n', 187)
            filtered = filter(lambda r: r[column2], (row for row in reader))
            yield column1, column2
            for row in filtered:
                formattedc1 = c1formatter(row[column1]) if c1formatter else row[column1]
                formattedc2 = c2formatter(row[column2]) if c2formatter else row[column2]
                yield (formattedc1, formattedc2)
        else:
            delimiter = ','
            concat = lambda a, b: f'{a}{b}'
            take_last = lambda c: c[-1]
            take_last_with = lambda c: take_last(c) + delimiter
            yield reader.fieldnames[0] + delimiter, reduce(concat, (name + delimiter for name in reader.fieldnames[1:]))
            for row in reader:
                head, *tail = row.items()
                yield take_last(head) + delimiter, reduce(concat, map(take_last_with, tail))


def hashdir(directory, hashfile=None):
    files = set(Path(f'{directory}/{filename}').resolve() for filename in all_files_in(directory))
    if hashfile is not None:
        files.discard(hashfile.resolve())

    hashes = set()
    for f in files:
        with open(f, 'rb') as openedfile:
            hashes.add(hashcon(openedfile.read()))
    return sorted(hashes)


def hashcon(content):
    hasher = sha256()
    hasher.update(content)
    return hasher.hexdigest()


class IOService:
    """
    A namespace for functions that perform filesystem actions
    """
    def read_file(filename: str) -> Either:
        path = Path(filename)
        return Right(path.open().read()) if path.exists() else Left(FileNotFoundError(filename))

    def handle_outcome(either: Either):
        result = either.value
        if isinstance(either, Right):
            return result.strip()
        else:
            raise result  # fail early


def format_records(
    records: Iterable[Dict[str, str]],
    *formatters: Tuple[str, Callable[[str], str]]
) -> Iterable[Tuple[str, str]]:
    yield dict([(header, None) for header, formatter in formatters])
    for record in records:
        yield dict([(header, formatter(record.get(header))) for header, formatter in formatters])


def build_csv(
    # TODO (withtwoemms) -- pass delimiter
    formatted_records: Iterable[Dict[str, str]],
) -> str:
    mapped_headers = ','.join(list(next(formatted_records)))
    mapped_records = map(lambda r: ','.join(r.values()), formatted_records)
    return reduce(lambda a, b: a + ',\n' + b, mapped_records, mapped_headers.rjust(32))


split = partial(methodcaller, 'split')
split_newlines, split_commas = split('\n'), split(',')
build_records = compose(dict, zip)
build_rows = compose(map(split_commas), split_newlines, IOService.handle_outcome, IOService.read_file)


def _handle_csv(
    csvfile: str,
    *columns_and_formatters: Tuple[str, Callable[..., Any]]
):
    rows = build_rows(csvfile)
    headers = next(rows)
    for col, _ in columns_and_formatters:
        if col not in headers:
            predicate, init = lambda a, b: f"{a}\n\t\t* {b}", '\n\t\t'
            exit_proc(f'\n\t❌ "{col}" not a valid column name in "{csvfile}": {reduce(predicate, not_none(headers), init)}\n', 187)
    records = iter(map(partial(build_records, headers), rows))

    formatted_records = format_records(records, *columns_and_formatters)

    return build_csv(formatted_records)

