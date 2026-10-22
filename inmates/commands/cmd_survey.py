import click

from inmates.cli import pass_environment
from inmates.rosters import ROSTER_INDEX
from inmates.rosters import read_index
from inmates.rosters import write_index
from inmates.survey import survey


MARKS = {'ok': '✅', 'moved': '↪️ ', 'none': '  '}


@click.command('survey', short_help='Probe every roster link.')
@click.option('-t', '--timeout', type=float, default=20, show_default=True, help='Seconds to wait on each site.')
@click.option('-n', '--dry-run', is_flag=True, help='Report without rewriting inmates.csv.')
@pass_environment
def cli(ctx, timeout, dry_run):
    """Checks each Roster Link in inmates.csv and records Status and Checked"""

    rows = read_index(ROSTER_INDEX)
    probes = survey(rows, timeout=timeout)

    for row, result in zip(rows, probes):
        if result.status == 'none':
            continue
        mark = MARKS.get(result.status, '❌')
        detail = f' -> {result.final_url}' if result.status == 'moved' else ''
        print(f"{mark} {row['IL County']:<20} {result.status:<12} {row['Platform'] or '':<12}{detail}")

    counted = sorted(((s, sum(p.status == s for p in probes)) for s in {p.status for p in probes} - {'none'}), key=lambda kv: -kv[1])
    print('\n' + '  '.join(f'{status}: {count}' for status, count in counted))

    if not dry_run:
        write_index(ROSTER_INDEX, rows)
        print(f'→ {ROSTER_INDEX}')
