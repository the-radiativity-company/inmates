import ipdb

from scrapy import Request
from scrapy import Spider
from pprint import pprint


class DekalbSpider(Spider):
    name = 'dekalb'

    def __init__(self, *args, **kwargs):
      self.domain = kwargs.get('domain')
      self.start_urls = [self.domain] if self.domain else kwargs.get('start_urls')

    def parse(self, response):
        profile_paths = response.xpath('//div[@id="intContentContainer"]/div/table//table[@class="inmateTable"]//a[@class="text2"]/@href').getall()
        for profile_path in profile_paths:
            yield Request(url=response.urljoin(profile_path), callback=self.parse_profile)

        next_page_paths = response.xpath('//div[@id="intContentContainer"]/div/table/tr[last()]/td/a/@href').getall()
        for next_page_path in next_page_paths:
            yield response.follow(response.urljoin(next_page_path), callback=self.parse)

    def parse_profile(self, profile):
        allkeys = [k.strip() for k in
                   profile.xpath('//*[@id="intContentContainer"]/div/table//table/tr/td/span/text()').extract()]
        allvals = profile.xpath('//*[@id="intContentContainer"]/div/table//table/tr/td/text()').extract()
        bondkey, bondval = allkeys.pop(), allvals.pop()
        keys = allkeys[:7]
        vals = allvals[:7]
        result = dict(zip(keys, vals))
        charges = allkeys[7:]
        result['Charges'] = charges
        result[bondkey] = bondval
        yield result

