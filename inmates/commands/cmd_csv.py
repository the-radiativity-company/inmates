import click
import inmates

from csv import DictReader
from os.path import dirname

from inmates.cli import pass_environment
from inmates.utils import handle_csv
from inmates.utils import _handle_csv


@click.command('csv', short_help='Performs operations on the csv')
@click.option('-c', '--column', help='Selects the given column for all rows.')
@pass_environment
def cli(ctx, column):
    """Extracts infromation from inmates.csv"""

    ## NOTE: this formatter turns a cell like "St. Claire County" -> "st-claire"
    #anchor_formatter = lambda anchor: anchor.rstrip('County').strip().lower().replace('. ', '-')

    #for record in handle_csv('inmates.csv', ('IL County', anchor_formatter), (column, None)):
    #    key, value = record
    #    print(f'{key.rjust(10)},{value}'.format(key, value))
    csv = _handle_csv('inmates.csv',
        ('IL County', lambda cell: cell.rstrip('County').rjust(20)),
        (column, lambda cell: cell)
    )
    print(csv)  # TODO (withtwoemms) -- log to STDOUT via ctx object

