"""The backoff retry middleware, exercised without a reactor."""
from scrapy import Request
from scrapy import Spider
from scrapy.settings import Settings
from scrapy.utils.project import get_project_settings

from inmates.scraper.middlewares import BackoffRetryMiddleware


def middleware(**overrides) -> BackoffRetryMiddleware:
    settings = Settings({'RETRY_ENABLED': True, 'RETRY_TIMES': 4, 'RETRY_BACKOFF_BASE': 2, **overrides})
    return BackoffRetryMiddleware(settings)


def test_first_attempt_goes_straight_out_and_retries_wait_twice_as_long_each_time():
    retry = middleware()
    assert retry.delay_for(Request('http://x/')) == 0
    assert [retry.delay_for(Request('http://x/', meta={'retry_times': n})) for n in (1, 2, 3, 4)] == [2, 4, 8, 16]
    assert middleware(RETRY_BACKOFF_BASE=0.5).delay_for(Request('http://x/', meta={'retry_times': 3})) == 2
    assert retry.process_request(Request('http://x/'), Spider('x')) is None


def test_project_settings_replace_the_stock_retry_middleware():
    settings = get_project_settings()
    middlewares = settings.getdict('DOWNLOADER_MIDDLEWARES')
    assert middlewares['scrapy.downloadermiddlewares.retry.RetryMiddleware'] is None
    assert middlewares['inmates.scraper.middlewares.BackoffRetryMiddleware'] == 550
    assert settings.getint('RETRY_TIMES') == 4
