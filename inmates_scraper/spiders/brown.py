# -*- coding: utf-8 -*-
import scrapy


class BrownSpider(scrapy.Spider):
    """
    name h3
    photo tag
    div with everything else
    lists of stuff
    photo filename matches bond id
    """
    name = 'brown'
    allowed_domains = ['brown']
    start_urls = ['https://www.brownso.org/agency-data/jail-roster/']

    def parse(self, response):
        table = response.css('.js-wpv-view-layout')

        names = table.xpath('h3')
        photo = table.css('h3 + div')
        other_stuff = table.xpath('//div[@style="float: right; width:70%;"]')
        # other stuff is being goofy, needs to be parsed sep
        items = zip(names, photo, other_stuff)
        for item in items:
            yield {
            'names': item[0].get(),
            'photo': item[1].get(),
            'other_stuff': item[2].get()
            }
