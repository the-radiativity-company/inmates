import click
import concurrent.futures
import inmates
import magic
import urllib.request

from csv import DictReader
from hashlib import sha256
from httpx import get as GET
from pathlib import Path
from os.path import dirname

from ..cli import pass_environment
from ..utils import hashcon, hashdir


hasher = sha256()


@click.command('download', short_help='Downloads artifacts from links in the CSV.')
@pass_environment
def cli(ctx):
    """Extracts infromation from inmates.csv"""

    csvfile = open('inmates.csv')
    filtered = filter(lambda r: r['Roster Link'], (row for row in DictReader(csvfile)))
    roster_links = ({'county': row['IL County'], 'link': row['Roster Link']} for row in filtered)
    artifact_direcotry = 'commissary'

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        call = {executor.submit(GET, rl['link'], timeout=10): rl for rl in roster_links}
        for future in concurrent.futures.as_completed(call):
            rl = call[future]
            try:
                response = future.result()
            except Exception as exc:
                ctx.error(f'generated an exception: {exc}')
            else:
                if response.status_code == 200:
                    ctx.log(f'{rl}')
                    filetype = magic.from_buffer(response.content[:2048])
                    filetype_extension = filetype.split(' ')[0].lower()
                    roster_artifact = rl['county'].rstrip('County').strip().lower().replace('. ', '-')
                    with open(f'{artifact_direcotry}/{roster_artifact}.{filetype_extension}', 'wb') as binfile:
                        hasher.update(response.content)
                        ctx.log(hasher.hexdigest())
                        binfile.write(response.content)

    csvfile.close()
    snapshot(artifact_direcotry, Path(f'{artifact_direcotry}/.hashfile'))


def snapshot(directory, hashfile=None):
    filehash_lists = snapshot_filehashes(directory, hashfile)
    if not lists_equivalent(*filehash_lists):
        with open(hashfile, 'w') as hfile:
            hfile.writelines(filehash_lists[-1])


def lists_equivalent(first, second):
    if type(first) == list and type(second) == list:
        if len(first) == len(second):
            for i in range(len(first) - 1):
                if first[i] == second[i]:
                    continue
                else:
                    return False
            return True
        else:
            return False
    else:
        return False


def snapshot_filehashes(directory, hashfile=None):
    hfile_contents = None

    if hashfile.exists():
        with open(hashfile.resolve(), 'r') as hfile:
            hfile_contents = hfile.readlines()
        open(hashfile.resolve(), 'w').close()
        for filehash in hashdir(directory, hashfile):
            with open(hashfile.resolve(), 'a') as hfile:
                hfile.write(filehash + '\n')
    else:
        for filehash in hashdir(directory, hashfile):
            with open(hashfile.resolve(), 'a') as hfile:
                hfile.write(filehash + '\n')

    with open(hashfile, 'r') as hfile:
        new_hfile_contents = hfile.readlines()

    return hfile_contents, new_hfile_contents

