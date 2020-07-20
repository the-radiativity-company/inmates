from inmates.utils import get_modules_from
from inmates.utils import handle_csv
from scrapy.settings import Settings
from shlex import split as split_args
from subprocess import run as run_proc
from sys import executable as python


anchor_formatter = lambda anchor: anchor.rstrip('County').strip().lower().replace('. ', '-')
all_links = dict(handle_csv('inmates.csv', ('IL County', anchor_formatter), ('Roster Link', None)))
spider_urls = dict((path.stem, all_links[path.stem]) for path in get_modules_from('inmates.scraper.spiders'))
for this_spider_name, this_spider_domain in spider_urls.items():
    run_proc(split_args(f'{python} -m scrapy crawl -a domain={this_spider_domain} {this_spider_name}'))
