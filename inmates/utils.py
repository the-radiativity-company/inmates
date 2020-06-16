from hashlib import sha256
from os import walk
from os.path import join as joinpath
from pathlib import Path


def all_files_in(directory):
    """returns a list of absolute file paths for all files below `directory` irrespective of nesting"""
    all_files_and_directories_below = []
    for root, dirs, files, in walk(directory, topdown=True):
        pruned_root = '/'.join(root.split('/')[1:])
        for name in files:
            if name != '__init__.py':  # NOTE: package init files are ignored
                all_files_and_directories_below.append(joinpath(pruned_root, name))
    return all_files_and_directories_below


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

