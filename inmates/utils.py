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

