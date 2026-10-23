"""The backoff retry middleware, exercised without a reactor."""
from scrapy import Request
from scrapy.settings import Settings
from scrapy.utils.project import get_project_settings

from inmates.scraper.middlewares import BackoffRetryMiddleware


def middleware(**overrides) -> BackoffRetryMiddleware:
    settings = Settings({'RETRY_ENABLED': True, 'RETRY_TIMES': 4, 'RETRY_WAIT_INITIAL': 2, 'RETRY_WAIT_JITTER': 1, 'RETRY_WAIT_MAX': 30, **overrides})
    retry = BackoffRetryMiddleware(settings)
    retry.uniform = lambda low, high: high  # the most jitter there is, so the tests are deterministic
    return retry


def retried(times: int) -> Request:
    return Request('http://x/', meta={'retry_times': times})


def test_first_attempt_goes_straight_out_and_retries_wait_twice_as_long_each_time_plus_jitter():
    retry = middleware()
    assert retry.delay_for(Request('http://x/')) == 0
    assert [retry.delay_for(retried(n)) for n in (1, 2, 3, 4)] == [3, 5, 9, 17]
    assert retry.process_request(Request('http://x/')) is None


def test_jitter_is_a_random_slice_of_its_setting_and_the_cap_wins():
    retry = middleware(RETRY_WAIT_JITTER=4)
    retry.uniform = lambda low, high: (low, high)[0] + 0.25 * (high - low)  # a fixed draw from the range
    assert retry.delay_for(retried(1)) == 3
    assert middleware(RETRY_WAIT_JITTER=0).delay_for(retried(3)) == 8
    assert middleware(RETRY_WAIT_MAX=10).delay_for(retried(4)) == 10
    assert middleware(RETRY_WAIT_MAX=10).delay_for(retried(9)) == 10


def test_project_settings_replace_the_stock_retry_middleware():
    settings = get_project_settings()
    middlewares = settings.getdict('DOWNLOADER_MIDDLEWARES')
    assert middlewares['scrapy.downloadermiddlewares.retry.RetryMiddleware'] is None
    assert middlewares['inmates.scraper.middlewares.BackoffRetryMiddleware'] == 550
    assert (settings.getint('RETRY_TIMES'), settings.getfloat('RETRY_WAIT_INITIAL'), settings.getfloat('RETRY_WAIT_JITTER'), settings.getfloat('RETRY_WAIT_MAX')) == (4, 2, 1, 30)
