import pdb
import scrapy


class MaconRoster(scrapy.Spider):
    """
    scraper for Macon Count inmates list
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
    name = "macon"

    def start_requests(self):
        urls = [
            'http://50.77.170.147/NewWorld.InmateInquiry/IL0580000?Name=&SubjectNumber=&BookingNumber=&InCustody=True&BookingFromDate=&BookingToDate=&Facility=',
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        table_body = response.xpath('//*[@id="Inmate_Index"]/div[2]/div[2]/table/tbody')[0]
        # in xpath, double slash any child node that matches the locator ('tr' in this case)
        rows = table_body.xpath('tr')
        for row in rows:
            yield {
                'Photo': row.css('.Photo').get(),
                'Name': row.css('.Name').get(),
                'SubjectNumber': row.css('.SubjectNumber::text').get(),
                'InCustody': row.css('.InCustody::text').get(),
                'ScheduledReleaseDate': row.css('.ScheduledReleaseDate::text').get(),
                'Race': row.css('.Race::text').get(),
                'Gender': row.css('.Gender::text').get(),
                'Height': row.css('.Height::text').get(),
                'Weight': row.css('.Weight::text').get(),
                'MultipleBookings': row.css('.MultipleBookings::text').get(),
                'HousingFacility': row.css('.HousingFacility::text').get()
            }
