import click
import inmates

from inmates.__init__ import prepare_fixtures
from inmates.cli import pass_environment


@click.command('fixtures', short_help='Prepares testing fixtures.')
@pass_environment
def cli(ctx):
    """Spiders crawl the commissary/ to produce local results against which one can test"""
    prepare_fixtures()
