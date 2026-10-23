"""Downloader middleware: retries that wait before trying again."""
import random

from scrapy.downloadermiddlewares.retry import RetryMiddleware


class BackoffRetryMiddleware(RetryMiddleware):
    """
    Scrapy's RetryMiddleware fires each retry at once, so a server that fails
    for a few seconds at a time (Macon's NewWorld inquiry answers one request
    in five with a 500) fails every attempt in a row. This one waits before
    each retry.

    The wait follows tenacity's wait_exponential_jitter: RETRY_WAIT_INITIAL
    seconds doubled per attempt, plus a random 0 to RETRY_WAIT_JITTER
    seconds so retries of several requests do not land in lockstep, capped
    at RETRY_WAIT_MAX. With the defaults (2, 1, 30) the waits run about
    2, 4, 8, 16 seconds and could never exceed 30.

    The wait is applied in process_request to a request that has already
    been retried (meta retry_times), by returning a Deferred that fires after
    the delay; the downloader waits on it before sending the request.
    """

    def __init__(self, settings):
        super().__init__(settings)
        self.initial = settings.getfloat('RETRY_WAIT_INITIAL', 2.0)
        self.jitter = settings.getfloat('RETRY_WAIT_JITTER', 1.0)
        self.max = settings.getfloat('RETRY_WAIT_MAX', 30.0)
        self.uniform = random.uniform

    def delay_for(self, request) -> float:
        attempt = request.meta.get('retry_times', 0)
        if not attempt:
            return 0.0
        return min(self.initial * 2 ** (attempt - 1) + self.uniform(0, self.jitter), self.max)

    def process_request(self, request, spider):
        delay = self.delay_for(request)
        if not delay:
            return None
        from twisted.internet import reactor  # after Scrapy has installed its reactor
        from twisted.internet.task import deferLater
        spider.logger.info('waiting %.1fs before retry %d of %s', delay, request.meta['retry_times'], request.url)
        return deferLater(reactor, delay, lambda: None)
