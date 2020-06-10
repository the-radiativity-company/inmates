import os

from pathlib import Path
from subprocess import CalledProcessError
from subprocess import PIPE
from subprocess import Popen as Proc
from typing import List


class TestSetupException(Exception): pass


test_spiders_dir = 'tests/scraper/spiders'
test_spiders = [Path(os.path.join(test_spiders_dir, file)) for file in os.listdir(test_spiders_dir)
    if file.endswith('.py')]

def run(spiders: List[Path]):
    # TODO (withtwoemms) -- use concurrent.futures
    for spider in spiders:
        print('SPIDER: ', spider)
        command = ['scrapy', 'runspider', '--set=ROBOTSTXT_OBEY=False', str(spider), '-o', f'tests/fixtures/{spider.stem}.json']

        with Proc(command, stdout=PIPE, stderr=PIPE) as proc:
            output, err = proc.communicate()

            if err and b'ERROR' in err:
                failure = err.decode("utf-8").strip().split('\n')[-1]
                raise TestSetupException(failure) from CalledProcessError(stderr=err, returncode=187, cmd=' '.join(proc.args))


run(test_spiders)
