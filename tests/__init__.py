import json
import os

from pathlib import Path
from re import match
from shlex import split
from subprocess import CalledProcessError
from subprocess import PIPE
from subprocess import Popen as Proc
from subprocess import run as runProc
from typing import ByteString
from typing import List
from typing import Tuple


class TestSetupException(Exception): pass


test_spiders_dir = 'tests/scraper/spiders'
test_fixtures_dir = 'tests/fixtures'

test_spiders = [Path(os.path.join(test_spiders_dir, file)) for file in os.listdir(test_spiders_dir)
    if file.endswith('.py')
    and not match(r'__.+__\.py', file)]


def prepare_fixtures(spiders: List[Path]) -> None:
    print('\nGenerating fixtures for:')
    # TODO (withtwoemms) -- use concurrent.futures to better handle multiple spiders
    for spider in spiders:
        print(f'....{spider}')
        spider_fixture = Path(f'{test_fixtures_dir}/{spider.stem}.json')
        spider_fixture.write_text('')

        fixture_generation_command = split(f'scrapy runspider --set=ROBOTSTXT_OBEY=False {str(spider)} -o {str(spider_fixture)}')
        runProc(fixture_generation_command, stderr=PIPE)

        gotten_contents = runProc(split(f'cat {str(spider_fixture)}'), stdout=PIPE).stdout.decode('utf-8')
        contents_dict = json.loads(gotten_contents)
        formatted_json = runProc(split('jq .'), stdout=PIPE, input=json.dumps(contents_dict[-5:]).encode())

        spider_fixture.write_text(formatted_json.stdout.decode('utf-8'))


prepare_fixtures(test_spiders)
