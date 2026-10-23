"""Downloader middleware: retries that wait before trying again."""
from scrapy.downloadermiddlewares.retry import RetryMiddleware


class BackoffRetryMiddleware(RetryMiddleware):
    """
    Scrapy's RetryMiddleware fires each retry at once, so a server that fails
    for a few seconds at a time (Macon's NewWorld inquiry answers one request
    in five with a 500) fails every attempt in a row. This one waits before
    each retry, RETRY_BACKOFF_BASE seconds doubled per attempt: with the
    default 2 that is 2, 4, 8, 16... seconds.

    The wait is applied in process_request to a request that has already
    been retried (meta retry_times), by returning a Deferred that fires after
    the delay; the downloader waits on it before sending the request.
    """

    def __init__(self, settings):
        super().__init__(settings)
        self.base = settings.getfloat('RETRY_BACKOFF_BASE', 2.0)

    def delay_for(self, request) -> float:
        attempt = request.meta.get('retry_times', 0)
        return self.base * 2 ** (attempt - 1) if attempt else 0.0

    def process_request(self, request, spider):
        delay = self.delay_for(request)
        if not delay:
            return None
        from twisted.internet import reactor  # after Scrapy has installed its reactor
        from twisted.internet.task import deferLater
        spider.logger.info('waiting %.1fs before retry %d of %s', delay, request.meta['retry_times'], request.url)
        return deferLater(reactor, delay, lambda: None)
