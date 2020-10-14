import click
import inmates

from csv import DictReader
from os.path import dirname

from inmates.cli import pass_environment
from inmates.utils import handle_csv


@click.command('csv', short_help='Performs operations on the csv')
@click.option('-c', '--column', help='Selects the given column for all rows.')
@pass_environment
def cli(ctx, column):
    """Extracts infromation from inmates.csv"""

    csv = handle_csv('inmates.csv',
        ('IL County', lambda cell: cell.rstrip('County').rjust(20)),
        (column, lambda cell: cell)
    )
    print(csv)  # TODO (withtwoemms) -- log to STDOUT via ctx object

