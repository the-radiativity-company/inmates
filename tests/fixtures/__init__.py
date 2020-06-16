import json
import os

from pathlib import Path
from typing import Dict


CURDIR = Path(__file__).absolute().parent


def all_files_in(directory):
    """returns a list of absolute file paths for all files below `directory` irrespective of nesting"""
    all_files_and_directories_below = []
    for root, dirs, files, in os.walk(directory, topdown=True):
        pruned_root = '/'.join(root.split('/')[1:])
        for name in files:
            if name != '__init__.py':  # NOTE: package init files are ignored
                all_files_and_directories_below.append(f'/{os.path.join(pruned_root, name)}')
    return all_files_and_directories_below


def jsonfrom(these_bytes: bytes) -> dict:
    return json.loads(these_bytes)


fixture_paths: Dict[str, Path] = {Path(file).name: Path(file) for file in all_files_in(CURDIR)}
