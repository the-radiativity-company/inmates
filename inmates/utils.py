from csv import DictReader
from functools import reduce
from hashlib import sha256
from importlib import import_module
from os import walk
from os.path import join as joinpath
from sys import exit
from sys import stdout
from pathlib import Path
from scrapy.crawler import Crawler
from scrapy.http import Request
from scrapy.settings import Settings
from typing import Any
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import Tuple
from urllib.parse import ParseResult
from urllib.parse import urlparse


def all_files_in(directory):
    """returns a list of absolute file paths for all files below `directory` irrespective of nesting"""
    all_files_and_directories_below = []
    for root, dirs, files, in walk(directory, topdown=True):
        for name in files:
            if not any(fragment in name for fragment in ['__main__.py', '__init__.py', 'cpython']):
                all_files_and_directories_below.append(joinpath(root, name))
    return all_files_and_directories_below


def get_modules_from(package: str):
    return set(Path(spider) for spider in all_files_in(package.replace('.', '/')))


def not_none(iterable: Iterable) -> Iterable:
    for item in filter(lambda item: item not in ['', None, [], (), {}], iterable):
        yield item


def exit_proc(msg, code, file=stdout):
    print(msg, file=file); exit(code)


def run_spiders_for(all_spider_info: Tuple[str, str, type], settings=None):
    """
    Leverages scrapy tooling to produce dictionary output.

    TODO (withtwoemms) -- use concurrent.futures to better handle multiple spiders
    """
    for spider_info in all_spider_info:
        print('SPIDER_INFRO: ', spider_info)
        try:
            spider_name, uri, spider_class = spider_info
            spider_instance = spider_class(start_urls=[uri])
            crawler = Crawler(spider_class, settings=settings)
            engine = crawler._create_engine()
            request = Request(url=uri, callback=lambda: '...making request...')
            deferred = engine.downloader.fetch(request, spider_instance)
            generated_output = spider_instance.parse(deferred.result)
            yield spider_name, generated_output
        except NotImplementedError:
            print('❌', f'{spider_name} (Please ensure a .parse method is defined)'); exit(187)
        except ValueError:
            print('❌', f'{spider_name} (Please ensure a .name attribute is defined)'); exit(187)


def is_uri(parse_result: ParseResult):
    return is_web_uri(parse_result) or is_file_uri(parse_result)


def is_web_uri(parse_result: ParseResult):
    return bool(parse_result.scheme in ('http', 'https')
                                    and parse_result.netloc)


def is_file_uri(parse_result: ParseResult):
    return bool(parse_result.scheme in ('file',)
                                    and not parse_result.netloc
                                    and parse_result.path)


def produce_spider_info_for(package: str, uris: Dict[str, str]):
    all_spider_names = set(Path(spider).stem for spider in all_files_in(package.replace('.', '/')))

    for spider_name in all_spider_names:
        uri = uris.get(spider_name)
        if not is_uri(urlparse(uri)):
            print('❌', f'InvalidURI for "{spider_name}": {uri}'); exit(187)

        expected_class = f'{spider_name.title()}Roster'
        try:
            spider_class = getattr(import_module(f'{package}.{spider_name}'), expected_class)
        except:
            print('❌', f'{spider_name} (Please ensure the spider class is called "{expected_class}")'); exit(187)

        # SpiderInfo
        yield (spider_name, uri, spider_class)


def handle_csv(
    file: str,
    column1_name_and_formatter: Tuple[str, Callable[..., Any]],
    column2_name_and_formatter: Tuple[str, Callable[..., Any]],
) -> Tuple[str, str]:
    column1, c1formatter = column1_name_and_formatter
    column2, c2formatter = column2_name_and_formatter
    if not column1:
        raise ValueError('The first column must be specified.')
    with open(file) as csvfile:
        reader = DictReader(csvfile)
        header = reader.fieldnames
        if column2:
            if column2 not in header:
                predicate, init = lambda a, b: f"{a}\n\t\t* {b}", '\n\t\t'
                print(f'\n\t❌ "{column2}" not found in: {reduce(predicate, not_none(header), init)}\n'); exit(187)
            filtered = filter(lambda r: r[column2], (row for row in reader))
            for row in filtered:
                formattedc1 = c1formatter(row[column1]) if c1formatter else row[column1]
                formattedc2 = c2formatter(row[column2]) if c2formatter else row[column2]
                yield (formattedc1, formattedc2)
        else:
            delimiter = ','
            concat = lambda a, b: f'{a}{b}'
            take_last = lambda c: c[-1]
            take_last_with = lambda c: take_last(c) + delimiter
            yield reader.fieldnames[0] + delimiter, reduce(concat, (name + delimiter for name in reader.fieldnames[1:]))
            for row in reader:
                head, *tail = row.items()
                yield take_last(head) + delimiter, reduce(concat, map(take_last_with, tail))


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

