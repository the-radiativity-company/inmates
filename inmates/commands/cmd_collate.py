import click

from inmates.cli import pass_environment
from inmates.rosters import PROJECT_ROOT
from inmates.rosters import roster_names
from inmates.rosters import rosters
from pathlib import Path
from shlex import split as split_args
from subprocess import run as run_proc
from sys import executable as python


@click.command('collate', short_help='Scrape inmate rosters.')
@click.option('-o', '--outdir', type=click.Path(path_type=Path), help='Directory for <roster>.json output.')
@click.option('-r', '--roster', type=click.Choice(roster_names()), help='Scrapes a given county.')
@pass_environment
def cli(ctx, outdir, roster):
    """Scrapes each county's roster with the spider for its platform, using info in inmates.csv"""

    selected = [r for r in rosters() if not roster or r.county == roster]

    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for r in selected:
        # -O overwrites; scrapy's -o appends to an existing file
        outopt = f'-O {outdir / r.county}.json -s LOG_LEVEL=WARNING' if outdir else ''
        command = f'{python} -m scrapy crawl -a domain={r.url} -a county={r.county} {r.spider} {outopt}'
        proc = run_proc(split_args(command), cwd=PROJECT_ROOT)
        ok = proc.returncode == 0
        failures += not ok
        print('✅' if ok else '❌', f'{r.county:<12}', f'({r.spider})' if r.spider != r.county else '')

    if failures:
        raise click.exceptions.Exit(1)
