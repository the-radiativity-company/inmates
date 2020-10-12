from functools import reduce
from functools import partial
from operator import methodcaller
from os import walk
from os.path import join as joinpath
from oslash.either import Left
from oslash.either import Either
from oslash.either import Right
from oslash.util import compose
from pathlib import Path
from pprint import pprint
from sys import argv
from sys import exit
from sys import stdout
from toolz.curried import map
from typing import Any
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import List
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


def handle_csv(
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

