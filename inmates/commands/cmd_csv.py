import click
import inmates

from csv import DictReader
from os.path import dirname

from ..cli import pass_environment


@click.command('csv', short_help='Performs operations on the csv')
@click.option('-c', '--column', help='Selects the given column for all rows.')
@pass_environment
def cli(ctx, column):
    """Extracts infromation from inmates.csv"""
    with open('inmates.csv') as csvfile:
        reader = DictReader(csvfile)
        if column:
            filtered = filter(lambda r: r[column], (row for row in reader))
            for row in filtered:
                print({row['IL County']: row[column]})
        else:
            list(print(dict(row)) for row in reader)
