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
    handle_csv('inmates.csv', column)

