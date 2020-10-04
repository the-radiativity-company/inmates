import ipdb

from pprint import pprint
from scrapy import Request
from scrapy import Spider
from urllib.parse import urlparse


class WillSpider(Spider):
    """
    scraper for Will County inmates list
    very similar to the Macon scraper
    list is in a simple paginated table
    the list can be filtered by some params controlled in the URL
    in this case, in InCustody is set to true so
    the other params could be used for programattic searches if needed

    TODO: the bond amount is on the detail tab for each inmate,
    how do we want to handle that? See here:
    https://docs.scrapy.org/en/latest/topics/request-response.html#topics-request-response-ref-request-callback-arguments
    for now I think we can scrape with the anchor tag so volunteers
    can look at the info?
    might need to process this in a pipeline

    TODO: tests
    """
    name = 'will'

    def __init__(self, *args, **kwargs):
      self.domain = kwargs.get('domain')
      self.start_urls = [self.domain] if self.domain else kwargs.get('start_urls')
      self.parsed_urls = [urlparse(url) for url in self.start_urls]

    def parse(self, response):
        """
        TODO (withtwoemms) -- handle pagination
        """
        table_body = response.xpath('//*[@id="Inmate_Index"]/div[2]/div[2]/table/tbody')[0]
        rows = table_body.xpath('tr')
        parsed_url = self.parsed_urls[0]
        for row in rows:
            profile_url = self.extract_profile_url(row)
            yield Request(url=profile_url, callback=self.parse_profile)

    def parse_profile(self, response):
        demography = response.xpath('//div[@id="DemographicInformation"]/ul/li')
        demographic_info = self.parse_demographic_data(demography)
        bookings = response.xpath('//div[@id="BookingHistory"]/div[@class="Booking"]')
        booking_data = [self.parse_booking_data(booking) for booking in bookings]
        demographic_info['Bookings'] = booking_data
        yield demographic_info

    def parse_demographic_data(self, demography):
        demographic_info = {}
        for element in demography:
            key = element.xpath('label/text()').get()
            value = element.xpath('span/text()').get()
            demographic_info.update({key: value})
        return demographic_info

    def parse_booking_data(self, booking):
        """
        TODO (withtwoemms) -- parse charges
        """
        booking_data = booking.xpath('./div[@class="BookingData"]')
        booking_info = self.parse_booking_info(booking_data)
        bond_info = self.parse_bond_info(booking_data)
        booking_info['bonds'] = bond_info
        return booking_info

    def parse_bond_info(self, booking_data):
        bond_info = []
        keys = booking_data.xpath('./div[@class="BookingBonds"]//table/thead//th/text()').getall()
        vals = booking_data.xpath('./div[@class="BookingBonds"]//table/tbody//td/text()').getall()
        for row in booking_data.xpath('./div[@class="BookingBonds"]//table/tbody/tr'):
            vals = row.xpath('./td/text()').getall()
            bond_info.append(dict(zip(keys, vals)))
        return bond_info

    def parse_booking_info(self, booking_data):
        booking_info = {}
        for element in booking_data.xpath('./ul[@class="FieldList"]/li'):
            key = element.xpath('label/text()').get()
            value = element.xpath('span/text()').get()
            booking_info.update({key: value})
        return booking_info

    def extract_profile_url(self, row):
        parsed_url = self.parsed_urls[0]
        url = f'{parsed_url.scheme}://{parsed_url.netloc}'
        path = row.xpath('./td[@class="Name"]/a/@href').get()
        profile_url = f'{url}{path}'
        return profile_url

