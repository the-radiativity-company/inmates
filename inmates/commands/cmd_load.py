import click

from datetime import datetime
from datetime import timezone
from pathlib import Path

from inmates.cli import pass_environment
from inmates.loader import connect
from inmates.loader import load_directory
from inmates.rosters import roster_urls
from inmates.rosters import spider_names


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat(sep=' ').replace('+00:00', '')


@click.command('load', short_help='Load scraped JSON into the SQLite database.')
@click.option('-i', '--indir', type=click.Path(exists=True, file_okay=False, path_type=Path), required=True,
              help='Directory holding <roster>.json files from `inmates collate -o`.')
@click.option('-d', '--database', type=click.Path(dir_okay=False, path_type=Path), default=Path('inmates.db'),
              show_default=True, help='SQLite database to create or update.')
@click.option('-r', '--roster', type=click.Choice(spider_names()), multiple=True,
              help='Load only these rosters (default: all).')
@click.option('--scraped-at', default=None, help='ISO timestamp of the scrape, UTC (default: now).')
@pass_environment
def cli(ctx, indir, database, roster, scraped_at):
    """Upserts each roster's JSON into the current-custody database."""

    counties = list(roster) or spider_names()
    stamp = scraped_at or utcnow_iso()
    conn = connect(database)
    try:
        results = load_directory(conn, indir, stamp, counties, roster_urls())
    finally:
        conn.close()

    for r in results:
        mark = {'ok': '✅', 'duplicate': '↩️ '}.get(r.status, '⚠️ ')
        print(f'{mark} {r.county:<10} {r.status:<9} records={r.record_count:<5} loaded={r.loaded:<5} released={r.released}')
    print(f'→ {database} @ {stamp}')
