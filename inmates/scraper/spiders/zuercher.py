from urllib.parse import urlsplit

from scrapy import Spider
from scrapy.http import JsonRequest


class ZuercherSpider(Spider):
    """
    CentralSquare's public inmate portal (formerly Zuercher Technologies),
    hosted at <agency>.zuercherportal.com. The page is a JavaScript app whose
    data comes from one JSON endpoint, so this spider talks to the endpoint
    directly: POST /api/portal/inmates/load with an empty name and a paging
    block returns everyone in custody, a page at a time.

    `domain` is the portal URL for a county, e.g.
    https://rockisland-911-il.zuercherportal.com/#/inmates; only its host is
    used. One record per person is emitted as the API sends it, minus the
    base64 mugshot. Note the API's 'dob' field actually carries an age.
    """
    name = 'zuercher'
    page_size = 100
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, domain=None, county=None, **kwargs):
        super().__init__(**kwargs)
        self.county = county
        parts = urlsplit(domain or '')
        self.root = f'{parts.scheme}://{parts.netloc}' if parts.netloc else ''
        self.start_urls = [f'{self.root}/api/portal/inmates/load'] if self.root else []

    def query(self, start: int) -> dict:
        return {
            'name': '', 'race': 'all', 'sex': 'all', 'cell_block': 'all', 'held_for_agency': 'any',
            'in_custody_date': '',
            'paging': {'count': self.page_size, 'start': start},
            'sorting': {'sort_by_column_tag': 'name', 'sort_descending': False},
        }

    def page_request(self, start: int) -> JsonRequest:
        return JsonRequest(self.start_urls[0], data=self.query(start), callback=self.parse, cb_kwargs={'start': start})

    async def start(self):
        if self.start_urls:
            yield self.page_request(0)

    def start_requests(self):  # Scrapy < 2.13
        if self.start_urls:
            yield self.page_request(0)

    def parse(self, response, start=0):
        payload = response.json()
        records = payload.get('records') or []
        for record in records:
            yield {key: value for key, value in record.items() if key != 'mugshot'}
        total = payload.get('total_record_count') or 0
        if records and start + len(records) < total:
            yield self.page_request(start + len(records))
