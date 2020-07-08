from csv import DictReader
from hashlib import sha256
from os import walk
from os.path import join as joinpath
from pathlib import Path
from typing import Any, Callable, Tuple


def all_files_in(directory):
    """returns a list of absolute file paths for all files below `directory` irrespective of nesting"""
    all_files_and_directories_below = []
    for root, dirs, files, in walk(directory, topdown=True):
        for name in files:
            if not any(fragment in name for fragment in ['__init__.py', 'cpython']):
                all_files_and_directories_below.append(joinpath(root, name))
    return all_files_and_directories_below


def handle_csv(
    file: str,
    column1_name_and_formatter: Tuple[str, Callable[..., Any]],
    column2_name_and_formatter: Tuple[str, Callable[..., Any]],
):
    column1, c1formatter = column1_name_and_formatter
    column2, c2formatter = column2_name_and_formatter
    if not column1:
        raise ValueError('The first column must be specified.')
    with open(file) as csvfile:
        reader = DictReader(csvfile)
        if column2:
            filtered = filter(lambda r: r[column2], (row for row in reader))
            for row in filtered:
                formattedc1 = c1formatter(row[column1]) if c1formatter else row[column1]
                formattedc2 = c1formatter(row[column2]) if c1formatter else row[column2]
                yield {formattedc1: formattedc2}
        else:
            for row in reader:
                yield dict(row)


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

