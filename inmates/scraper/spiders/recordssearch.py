from urllib.parse import urlsplit

from scrapy import Request
from scrapy import Spider


class RecordsSearchSpider(Spider):
    """
    Tyler Technologies' Corrections Records Search, the roster behind
    https://correctionsrecordssearch.com/<alias> (Peoria). The page is an
    Angular app whose data comes from a public JSON API, so this spider talks
    to the API directly: GET /instances/lookup?alias=<alias> turns the URL's
    alias into an instance id, then GET /instances/<id>/inmates pages through
    everyone in custody.

    `domain` is the roster URL for a county; its last path segment is the
    alias. One record per person is emitted as the API sends it: name,
    demographics, arrests with charges, and bonds. Mugshots are served from a
    separate endpoint and never fetched.
    """
    name = 'recordssearch'
    api = 'https://api.correctionsrecordssearch.com'
    page_size = 500
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, domain=None, county=None, **kwargs):
        super().__init__(**kwargs)
        self.county = county
        self.alias = urlsplit(domain or '').path.strip('/').split('/')[-1]
        self.start_urls = [f'{self.api}/instances/lookup?alias={self.alias}'] if self.alias else []

    def page_request(self, instance_id: str, page: int) -> Request:
        url = f'{self.api}/instances/{instance_id}/inmates?page-size={self.page_size}&page-number={page}&sort-by=arrestDate&sort=desc'
        return Request(url, callback=self.parse_page, cb_kwargs={'instance_id': instance_id, 'page': page})

    def parse(self, response):
        instance_id = response.json().get('instanceId')
        if instance_id:
            yield self.page_request(instance_id, 1)

    def parse_page(self, response, instance_id, page):
        payload = response.json()
        records = payload.get('inmates') or []
        yield from records
        total = (payload.get('pagination') or {}).get('total') or 0
        if records and page * self.page_size < total:
            yield self.page_request(instance_id, page + 1)
