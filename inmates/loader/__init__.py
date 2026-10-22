"""Turns scraped roster JSON into the current-custody SQLite database."""
from inmates.loader.db import connect
from inmates.loader.db import load_county
from inmates.loader.db import load_directory
from inmates.loader.db import RunResult
from inmates.loader.normalize import normalize

__all__ = ['connect', 'load_county', 'load_directory', 'normalize', 'RunResult']
