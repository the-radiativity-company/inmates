import click
import inmates

from csv import DictReader
from os.path import dirname

from ..cli import pass_environment


@click.command('csv', short_help='Performs operations on the csv')
@pass_environment
def cli(ctx):
    """Extracts infromation from inmates.csv"""
    with open('inmates.csv') as csvfile:
        print(csvfile)
        reader = DictReader(csvfile)
        for row in reader:
            print(dict(row))
