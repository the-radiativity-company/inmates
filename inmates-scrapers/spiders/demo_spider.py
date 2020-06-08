import pdb
import scrapy


class MaconRoster(scrapy.Spider):
    name = "Macon County"

    def start_requests(self):
        urls = [
            'http://50.77.170.147/NewWorld.InmateInquiry/IL0580000?Name=&SubjectNumber=&BookingNumber=&BookingFromDate=&BookingToDate=&Facility=',
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        thebody = response.xpath('//*[@id="Inmate_Index"]/div[2]/div[2]/table/tbody')[0]
        rows = thebody.xpath('tr')
        for row in rows:
            result = {}
            for td in row.xpath('td'):
                result.update({
                    'SubjectNumber': td.css('.SubjectNumber::text').get(),
                    'InCustody': td.css('.InCustody::text').get(),
                    'ScheduledReleaseDate': td.css('.ScheduledReleaseDate::text').get(),
                    'Race': td.css('.Race::text').get(),
                    'Gender': td.css('.Gender::text').get(),
                    'Height': td.css('.Height::text').get(),
                    'Weight': td.css('.Weight::text').get(),
                    'MultipleBookings': td.css('.MultipleBookings::text').get(),
                    'HousingFacility': td.css('.HousingFacility::text').get()
                })
            yield result
