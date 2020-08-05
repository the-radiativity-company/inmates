from inmates.utils import exit_proc
from inmates.utils import get_modules_from
from inmates.utils import handle_csv
from pathlib import Path
from scrapy.settings import Settings
from shlex import split as split_args
from subprocess import run as run_proc
from sys import argv
from sys import executable as python
from sys import exit


anchor_formatter = lambda anchor: anchor.rstrip('County').strip().lower().replace('. ', '-')
all_links = dict(handle_csv('inmates.csv', ('IL County', anchor_formatter), ('Roster Link', None)))
spider_urls = dict((path.stem, all_links[path.stem]) for path in get_modules_from('inmates.scraper.spiders'))

outdir = argv[1:]

if outdir:
    outdirpath = Path(outdir[0])
    outdirpath.mkdir(exist_ok=True)
else:
    outdirpath = None

for spider, url in spider_urls.items():
    outopt = f'-o {outdirpath}/{spider}.json -s LOG_ENABLED=False' if outdirpath else ''
    run_proc(split_args(f'{python} -m scrapy crawl -a domain={url} {spider} {outopt}'))
    print('✅', spider)

