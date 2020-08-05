import scrapy


class WillRoster(scrapy.Spider):
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

    def parse(self, response):
        table_body = response.xpath('//*[@id="Inmate_Index"]/div[2]/div[2]/table/tbody')[0]
        next_page = response.css('.Next::attr(href)').get()
        # TODO: a good clean way to scrape these details
        inmate_detail_link = response.css('td.Name > a').get()

        # in xpath, double slash any child node that matches the locator ('tr' in this case)
        rows = table_body.xpath('tr')
        for row in rows:
            yield {
                'Name': row.css('.Name').get(),
                'InCustody': row.css('.InCustody::text').get(),
                'Race': row.css('.Race::text').get(),
                'Gender': row.css('.Gender::text').get(),
                'Height': row.css('.Height::text').get(),
                'Weight': row.css('.Weight::text').get(),
                'MultipleBookings': row.css('.MultipleBookings::text').get(),
                'HousingFacility': row.css('.HousingFacility::text').get()
            }


        if next_page is not None:
            yield response.follow(next_page, callback=self.parse)
