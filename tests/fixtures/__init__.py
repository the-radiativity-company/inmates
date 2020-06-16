import json
import os

from inmates.utils import all_files_in

from pathlib import Path
from typing import Dict


CURDIR = Path(__file__).absolute().parent


def jsonfrom(these_bytes: bytes) -> dict:
    return json.loads(these_bytes)


fixture_paths: Dict[str, Path] = {Path(file).name: Path(file) for file in all_files_in(CURDIR)}
