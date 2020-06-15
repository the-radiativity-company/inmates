import json
import os

from pathlib import Path
from re import match
from shlex import split
from subprocess import CalledProcessError
from subprocess import PIPE
from subprocess import Popen as Proc
from subprocess import run as runProc
from typing import ByteString
from typing import List
from typing import Tuple


class TestSetupException(Exception): pass


test_spiders_dir = 'tests/scraper/spiders'
test_fixtures_dir = 'tests/fixtures'

test_spiders = [Path(os.path.join(test_spiders_dir, file)) for file in os.listdir(test_spiders_dir)
    if file.endswith('.py')
    and not match(r'__.+__\.py', file)]


def prepare_fixtures(spiders: List[Path]) -> None:
    print('\nGenerating fixtures for:')
    # TODO (withtwoemms) -- use concurrent.futures to better handle multiple spiders
    for spider in spiders:
        print(f'....{spider}')
        spider_fixture = Path(f'{test_fixtures_dir}/{spider.stem}.json')
        spider_fixture.write_text('')

        fixture_generation_command = split(f'scrapy runspider --set=ROBOTSTXT_OBEY=False {str(spider)} -o {str(spider_fixture)}')
        handle(*execute(Proc(fixture_generation_command, stderr=PIPE)))

        contents_proc = Proc(split(f'cat {str(spider_fixture)}'), stdout=PIPE)
        contents_dict = json.loads(handle(*execute(contents_proc)).decode('utf-8'))
        ran = runProc(split('jq .'), stdout=PIPE, input=json.dumps(contents_dict[-5:]).encode())
        spider_fixture.write_text(ran.stdout.decode('utf-8'))


def execute(proc: Proc = None) -> Tuple[bytes, bytes]:
    out, err = b'', b''
    if proc:
        out, err = proc.communicate()
        proc.wait()
    return out, err


def handle(out: ByteString, err: ByteString):
    if err and b'ERROR' in err:
        failure = err.decode("utf-8").strip().split('\n')[-1]
        raise TestSetupException(failure) from CalledProcessError(stderr=err, returncode=187, cmd=' '.join(proc.args))
    return out


def chain(proc: Proc, *commands: List[str]):
    commands = list(commands)
    if commands:
        return chain(Proc(commands.pop(0), stdin=proc.stdout, stdout=PIPE), *commands)
    else:
        return proc


prepare_fixtures(test_spiders)
