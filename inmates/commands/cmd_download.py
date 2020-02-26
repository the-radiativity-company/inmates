import click
import concurrent.futures
import inmates
import urllib.request

from csv import DictReader
from httpx import get as GET
from os.path import dirname

from ..cli import pass_environment


@click.command('download', short_help='Downloads artifacts from links in the CSV.')
@pass_environment
def cli(ctx):
    """Extracts infromation from inmates.csv"""

    csvfile = open('inmates.csv')
    filtered = filter(lambda r: r['Roster Link'], (row for row in DictReader(csvfile)))
    roster_links = ({'county': row['IL County'], 'link': row['Roster Link']} for row in filtered)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        call = {executor.submit(GET, rl['link'], timeout=10): rl for rl in roster_links}
        for future in concurrent.futures.as_completed(call):
            url = call[future]
            try:
                data = future.result()
            except Exception as exc:
                print(f'{url} generated an exception: {exc}')
            else:
                print(f'{url} page is {data} bytes')

    csvfile.close()
