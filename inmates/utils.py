from hashlib import sha256
from os import walk
from os.path import join as joinpath
from pathlib import Path


hasher = sha256()


# TODO -- improve efficiency
def snapshot(directory, hashfile=None, changedfile=None):
    old, new = snapshot_filehashes(directory, hashfile, changedfile)
    changed = dict(set(new).difference(set(old)))
    merged = {**dict(old), **dict(new)}
    with open(hashfile, 'w') as hfile:
        hfile.writelines(list(f'{pair[0]},{pair[1]}\n' for pair in sorted(merged.items())))
    with open(changedfile, 'w') as cfile:
        cfile.writelines(list(f'{pair[0]},{pair[1]}\n' for pair in sorted(changed.items())))


# TODO -- improve efficiency
def snapshot_filehashes(directory, hashfile=None, changedfile=None):
    hfile_contents = None

    if hashfile.exists():
        with open(hashfile.resolve(), 'r') as hfile:
            old_hfile_contents = list(tuple(pair.strip().split(',')) for pair in hfile.readlines())

        new_hfile_contents = hashdir(directory, hashfile, changedfile)

        open(hashfile.resolve(), 'w').close()
        # TODO -- move functionality, below, to own function
        for county, filehash in new_hfile_contents:
            with open(hashfile.resolve(), 'a') as hfile:
                hfile.write(f'{county},{filehash}\n')
        return old_hfile_contents, new_hfile_contents
    else:
        for county, filehash in hashdir(directory, hashfile, changedfile):
            with open(hashfile.resolve(), 'a') as hfile:
                hfile.write(f'{county},{filehash}\n')

        with open(hashfile, 'r') as hfile:
            new_hfile_contents = list(tuple(pair.strip().split(',')) for pair in hfile.readlines())

        return list(), new_hfile_contents


def all_files_in(directory):
    all_files_and_directories_below = []
    for root, dirs, files, in walk(directory, topdown=True):
        pruned_root = '/'.join(root.split('/')[1:])
        for name in files:
            all_files_and_directories_below.append(joinpath(pruned_root, name))
    return all_files_and_directories_below


def hashdir(directory, hashfile=None, changedfile=None):
    files = set(Path(f'{directory}/{filename}').resolve() for filename in all_files_in(directory))
    # TODO -- devise more convenient means of excluding files
    if hashfile is not None:
        files.discard(hashfile.resolve())
        files.discard(changedfile.resolve())
        files.discard(Path(f'{directory}/.gitignore').resolve())

    hashes = set()
    for f in files:
        with open(f, 'rb') as openedfile:
            filecontents = openedfile.read()
            hashes.add((f.stem, hashcon(filecontents)))
    return sorted(hashes)


def hashcon(content):
    hasher = sha256()
    hasher.update(content)
    return hasher.hexdigest()

