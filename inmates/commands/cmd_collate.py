import click

from inmates.cli import pass_environment
from inmates.rosters import PROJECT_ROOT
from inmates.rosters import roster_urls
from inmates.rosters import spider_names
from pathlib import Path
from shlex import split as split_args
from subprocess import run as run_proc
from sys import executable as python


@click.command('collate', short_help='Scrape inmate rosters.')
@click.option('-o', '--outdir', type=click.Path(path_type=Path), help='Directory for <roster>.json output.')
@click.option('-r', '--roster', type=click.Choice(spider_names()), help='Scrapes a given roster.')
@pass_environment
def cli(ctx, outdir, roster):
    """Scrapes rosters for Spiders using info in inmates.csv"""

    urls = roster_urls()
    selected = {roster: urls[roster]} if roster else urls

    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for name, url in selected.items():
        # -O overwrites; scrapy's -o appends to an existing file
        outopt = f'-O {outdir / name}.json -s LOG_LEVEL=WARNING' if outdir else ''
        proc = run_proc(split_args(f'{python} -m scrapy crawl -a domain={url} {name} {outopt}'), cwd=PROJECT_ROOT)
        ok = proc.returncode == 0
        failures += not ok
        print('✅' if ok else '❌', name)

    if failures:
        raise click.exceptions.Exit(1)
