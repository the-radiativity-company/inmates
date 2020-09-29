import ipdb

from scrapy import Spider
from scrapy import FormRequest
from scrapy import Request


class StclairSpider(Spider):
    name = 'stclair'

    def __init__(self, *args, **kwargs):
      self.domain = kwargs.get('domain')
      self.start_urls = [self.domain] if self.domain else kwargs.get('start_urls')

    def parse(self, response):
        response.xpath('//input[@id="txtLastName"]')
        formid = 'txtLastName'
        for formdata in [{formid: chr(x)} for x in range(97, 123)]:  # a-z
            yield FormRequest.from_response(response,
                                            formid=formid,
                                            formdata=formdata,
                                            callback=self.handle_form)

    def handle_form(self, form_response):
        table_rows = form_response.xpath('//table[@id="nameResultsTable"]').xpath('tr')
        for tr in table_rows[1:]:
            yield Request(url=tr.attrib['onclick'].split('showProgress();location.href=')[-1].strip("'"),
                          callback=self.parse_profile)

    def parse_profile(self, profile_response):
        profile = profile_response.xpath('//*[@id="mvcContainer-982"]/div/div/div[1]/div[2]/table/tr[th and td]')
        result = {}
        for data in profile:
            key = data.xpath('./th/text()').pop().extract().strip()
            val = data.xpath('./td/text()').pop().extract().strip()
            result[key] = val

        charges = []
        # NOTE: fails when using comprehension
        for charge in profile_response.xpath('//*[@id="mvcContainer-982"]/div/div/div[2]/div/text()'):  #
            charge = charge.extract().strip()
            if charge:
                charges.append(charge)

        result['Charges'] = charges

        yield result

