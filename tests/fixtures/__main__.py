import json
import os

from importlib import import_module
from itertools import islice as take
from pathlib import Path
from scrapy.crawler import Crawler
from scrapy.http import Request
from scrapy.settings import Settings
from typing import Tuple

from inmates.utils import all_files_in


settings = Settings()
settings.setmodule('inmates.scraper.settings', priority='project')


def produce_spider_info_for(module_name: str, commissary: Path):
    all_roster_paths = dict([Path(site).stem, Path(site).absolute()] for site in all_files_in(commissary))
    all_spider_names = set(Path(spider).stem for spider in all_files_in(module_name.replace('.', '/')))

    for spider_name in all_spider_names:
        local_uri = all_roster_paths.get(spider_name).absolute().as_uri(),
        spider_class = getattr(import_module(f'{module_name}.{spider_name}'), f'{spider_name.title()}Roster')

        # SpiderInfo
        yield (spider_name, local_uri, spider_class)


def prepare_fixtures_from(all_spider_info: Tuple[str, str, type]):
    """
    Leverages scrapy tooling to produce dictionary output.

    TODO (withtwoemms) -- use concurrent.futures to better handle multiple spiders
    """
    for spider_info in all_spider_info:
        spider_name, local_uri, spider_class = spider_info
        spider_instance = spider_class(start_urls=[local_uri])
        crawler = Crawler(spider_class, settings=settings)
        engine = crawler._create_engine()
        request = Request(url=local_uri, callback=spider_instance.parse)
        deferred = engine.downloader.fetch(request, spider_instance)
        generated_output = spider_instance.parse(deferred.result)
        yield spider_name, generated_output


def write_prepared_fixtures(name, fixtures, fixtures_dir: Path, fixture_type: str):
    # Validation
    if not fixture_type in ['json']:
        raise ValueError(f'Currently, "{fixture_type}" is not supported.')

    spider_fixture_path = fixtures_dir.joinpath(f'{name}.{fixture_type}')
    spider_fixture_path.write_text('')

    spider_fixture_path.write_text(json.dumps(list(take(fixtures, 3)), indent=4, sort_keys=True))


commissary = Path(__file__).absolute().parent.parent.parent.joinpath('commissary')
test_fixtures_dir = Path('tests/fixtures')

def prepare_fixtures():
    for name, fixtures in prepare_fixtures_from(produce_spider_info_for('inmates.scraper.spiders', commissary)):
        write_prepared_fixtures(
            name,
            fixtures,
            fixtures_dir=test_fixtures_dir,
            fixture_type='json'
        )

