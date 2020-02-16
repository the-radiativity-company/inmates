import click
import inmates

from os.path import dirname

from ..cli import pass_environment


@click.command('csv', short_help='Performs operations on the csv')
@pass_environment
def cli(ctx):
    """Extracts infromation from inmates.csv"""
    pass

