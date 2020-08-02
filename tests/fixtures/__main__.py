import json
import os

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from importlib import import_module
from itertools import islice as take
from pathlib import Path
from scrapy.crawler import Crawler
from scrapy.http import Request
from scrapy.settings import Settings
from sys import exit
from typing import Tuple

from inmates.utils import all_files_in


settings = Settings()
settings.setmodule('inmates.scraper.settings.base', priority='project')
debug_mode = settings['INMATES_DEBUG_MODE']

def produce_spider_info_for(module_name: str, commissary: Path):
    all_roster_paths = dict([Path(site).stem, Path(site).absolute()] for site in all_files_in(commissary))
    all_spider_names = set(Path(spider).stem for spider in all_files_in(module_name.replace('.', '/')))

    for spider_name in all_spider_names:
        roster_path = all_roster_paths.get(spider_name)
        if not roster_path:
            if os.environ.get(debug_mode): raise e
            print('❌', f'{spider_name} (It seems there is no commissary/ entry)'); exit(187)
        local_uri = roster_path.absolute().as_uri()

        expected_class = f'{spider_name.title()}Roster'
        try:
            spider_class = getattr(import_module(f'{module_name}.{spider_name}'), expected_class)
        except Exception as e:
            if os.environ.get(debug_mode): raise e
            print('❌', f'{spider_name} (Please ensure the spider class is called "{expected_class}")'); exit(187)

        # SpiderInfo
        yield (spider_name, local_uri, spider_class)


def prepare_fixtures_from(all_spider_info: Tuple[str, str, type]):
    """
    Leverages scrapy tooling to produce dictionary output.

    TODO (withtwoemms) -- use concurrent.futures to better handle multiple spiders
    """
    for spider_info in all_spider_info:
        try:
            spider_name, local_uri, spider_class = spider_info
            spider_instance = spider_class(start_urls=[local_uri])
            crawler = Crawler(spider_class, settings=settings)
            engine = crawler._create_engine()
            request = Request(url=local_uri, callback=lambda: '...making request...')
            deferred = engine.downloader.fetch(request, spider_instance)
            generated_output = spider_instance.parse(deferred.result)
            yield spider_name, generated_output
        except NotImplementedError as e:
            if os.environ.get(debug_mode): raise e
            print('❌', f'{spider_name} (Please ensure a .parse method is defined)'); exit(187)
        except ValueError as e:
            if os.environ.get(debug_mode): raise e
            print('❌', f'{spider_name} (Please ensure a .name attribute is defined)'); exit(187)


def write_prepared_fixtures(name, fixtures, fixtures_dir: Path, fixture_type: str):
    # Validation
    if not fixture_type in ['json']:
        raise ValueError(f'Currently, "{fixture_type}" is not supported.')
    if not fixtures:
        if os.environ.get(debug_mode): raise RuntimeError
        print('❌', f'{name} (Please yield data from the .parse method)'); exit(187)

    spider_fixture_path = fixtures_dir.joinpath(f'{name}.{fixture_type}')
    spider_fixture_path.write_text('')

    spider_fixture_path.write_text(json.dumps(list(take(fixtures, 3)), indent=4, sort_keys=True))
    print('✅', name)


commissary = Path(__file__).absolute().parent.parent.parent.joinpath('commissary')
test_fixtures_dir = Path('tests/fixtures')

def prepare_fixtures():
    all_spider_info = produce_spider_info_for('inmates.scraper.spiders', commissary)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(
                write_prepared_fixtures,
                name,
                fixtures,
                fixtures_dir=test_fixtures_dir,
                fixture_type='json'
            ): name for name, fixtures in prepare_fixtures_from(all_spider_info)
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                future.result()
            except Exception as e:
                if os.environ.get(debug_mode): raise e


prepare_fixtures()

