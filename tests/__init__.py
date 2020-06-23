import json
import os

from inmates.utils import all_files_in

from importlib import import_module
from pathlib import Path
from re import match
from scrapy.crawler import Crawler
from scrapy.http import Request
from scrapy.http import Response
from scrapy.settings import Settings
from shlex import split
from subprocess import CalledProcessError
from subprocess import PIPE
from subprocess import Popen as Proc
from subprocess import run as runProc
from typing import ByteString
from typing import List
from typing import Tuple


def prepare_fixtures_for(spider_paths: List[Path], fixtures_dir: Path, fixture_type: str) -> None:
    """
    This function takes a list of spiders--e.g spiders targeting the "commissary/"--and produces a formatted list of fixtures.
    It's purpose is to generate structs that represent an "inmate" against which spider tests can be written.
    Steps to perform this feat are three-fold:
        1. generate raw spider output
        2. formate that output
        3. persist the formatted output

    TODO (withtwoemms) -- use concurrent.futures to better handle multiple spiders
    """
    # Validation
    if not all(path.exists() for path in spider_paths + [fixtures_dir]):
        raise ValueError(f'The output directory, "{fixtures_dir}", and all spiders from which to create fixtures must already exist.')
    if not fixture_type in ['json']:
        raise ValueError(f'Currently, "{fixture_type}" is not supported.')


    print('\nGenerating fixtures for:')
    for spider_path in spider_paths:
        print(f'....{spider_path}')
        spider_fixture_path = fixtures_dir.joinpath(f'{spider_path.stem}.{fixture_type}')
        spider_fixture_path.write_text('')

        # STEP 1: leverage scrapy to generate some raw output
        fixture_generation_command = split(f'scrapy runspider --set=ROBOTSTXT_OBEY=False {str(spider_path)} -o {str(spider_fixture_path)}')
        runProc(fixture_generation_command, stderr=PIPE)  # NOTE: PIPE used to stash what would flow to stdout

        # STEP 2: format and truncate that output
        gotten_contents = runProc(split(f'cat {str(spider_fixture_path)}'), stdout=PIPE).stdout.decode('utf-8')
        contents_dict = json.loads(gotten_contents)  # NOTE: raw output is truncated
        formatted_json = runProc(split('jq .'), stdout=PIPE, input=json.dumps(contents_dict[-5:]).encode())

        # STEP 3: write the formatted output to disk
        spider_fixture_path.write_text(formatted_json.stdout.decode('utf-8'))


commissary = Path(__file__).absolute().parent.parent.joinpath('commissary')
# all_roster_paths = set(Path(site).stem for site in all_files_in(commissary))
all_roster_paths = dict([Path(site).stem, Path(site).absolute()] for site in all_files_in(commissary))
all_spider_names = set(Path(spider).stem for spider in all_files_in('inmates/scraper/spiders'))


spider_classes = {
    spider_name: {
        'class': getattr(import_module(f'inmates.scraper.spiders.{spider_name}'), f'{spider_name.title()}Roster'),
        'url': all_roster_paths.get(spider_name)
    } for spider_name in all_spider_names
}

all_spider_info = [
    (
        spider_name,
        getattr(import_module(f'inmates.scraper.spiders.{spider_name}'), f'{spider_name.title()}Roster'),
        all_roster_paths.get(spider_name)
    ) for spider_name in all_spider_names
]

for spider_info in all_spider_info:
    spider_name, spider_class, local_uri = spider_info
    print(spider_name)

from pprint import pprint
pprint(spider_info)
# for name, class_and_url in spider_classes.items():
#     pprint(class_and_url['url'])
#     pprint(class_and_url)
#
#     instance = class_and_url['class'](start_urls=[str(class_and_url['url'].absolute().as_uri())])
#     print(instance)
#     pprint(dir(instance))
#     result = instance.start_requests()
#     # print('RESULT: ', result)
#     settings = Settings()
#     settings.setmodule('inmates.scraper.settings', priority='project')
#     # pprint(settings.attributes)
#     crawler = Crawler(class_and_url['class'], settings=settings)
#     engine = crawler._create_engine()
#     r = engine.downloader.fetch(Request(url=class_and_url['url'].absolute().as_uri(), callback=instance.parse), instance)
#     print(r)
#     pprint(dir(r))
#     print(r.result)
#     print(type(r.result))
#     pprint(dir(r.result))
#     pprint(list(instance.parse(r.result)))

test_spiders_dir = 'tests/scraper/spiders'
test_fixtures_dir = Path('tests/fixtures')
test_spiders = [Path(os.path.join(test_spiders_dir, file)) for file in os.listdir(test_spiders_dir)
    if file.endswith('.py')
    and not match(r'__.+__\.py', file)]


def prepare_fixtures():
    prepare_fixtures_for(
        spider_paths=test_spiders,
        fixtures_dir=test_fixtures_dir,
        fixture_type='json'
    )

