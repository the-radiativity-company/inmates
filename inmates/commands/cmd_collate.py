import click

from inmates.cli import pass_environment
from inmates.utils import build_dict
from inmates.utils import exit_proc
from inmates.utils import format_records
from inmates.utils import get_modules_from
from inmates.utils import handle_csv
from inmates.utils import produce_records
from pathlib import Path
from scrapy.settings import Settings
from shlex import split as split_args
from subprocess import run as run_proc
from sys import argv
from sys import executable as python
from sys import exit


spider_paths = get_modules_from('inmates.scraper.spiders')


@click.command('collate', short_help='Scrape inmate rosters.')
@click.option('-o', '--outdir', type=click.Path(), help='Output directory.')
@click.option('-r', '--roster', type=click.Choice(list(map(lambda sp: sp.stem, spider_paths))), help='Scrapes a given roster.')
@pass_environment
def cli(ctx, outdir, roster):
    """Scrapes rosters for Spiders using info in inmates.csv"""

    all_links = build_dict(
        format_records(
            produce_records('inmates.csv'),
            ('IL County', lambda cell: cell.replace(' County', '').replace('. ', '').lower()),
            ('Roster Link', lambda cell: cell)
        )
    )

    roster_urls = dict((path.stem, all_links[path.stem]) for path in spider_paths)

    if outdir:
        outdirpath = Path(outdir)
        outdirpath.mkdir(exist_ok=True)
    else:
        outdirpath = None

    if roster:
        outopt = f'-o {outdirpath}/{roster}.json -s LOG_ENABLED=False' if outdirpath else ''
        run_proc(split_args(f'{python} -m scrapy crawl -a domain={roster_urls[roster]} {roster} {outopt}'))
        print('✅', roster)
    else:
        for roster, url in roster_urls.items():
            outopt = f'-o {outdirpath}/{roster}.json -s LOG_ENABLED=False' if outdirpath else ''
            run_proc(split_args(f'{python} -m scrapy crawl -a domain={url} {roster} {outopt}'))
            print('✅', roster)
