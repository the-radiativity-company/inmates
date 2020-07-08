from csv import DictReader
from hashlib import sha256
from os import walk
from os.path import join as joinpath
from pathlib import Path


def all_files_in(directory):
    """returns a list of absolute file paths for all files below `directory` irrespective of nesting"""
    all_files_and_directories_below = []
    for root, dirs, files, in walk(directory, topdown=True):
        for name in files:
            if not any(fragment in name for fragment in ['__init__.py', 'cpython']):
                all_files_and_directories_below.append(joinpath(root, name))
    return all_files_and_directories_below


def handle_csv(file: str, column: str = None):
    with open('inmates.csv') as csvfile:
        reader = DictReader(csvfile)
        if column:
            filtered = filter(lambda r: r[column], (row for row in reader))
            for row in filtered:
                print({row['IL County']: row[column]})
        else:
            list(print(dict(row)) for row in reader)


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

