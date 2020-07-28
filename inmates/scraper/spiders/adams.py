# -*- coding: utf-8 -*-
import scrapy
import pdfminer


class AdamsSpider(scrapy.Spider):
    name = 'adams'
    allowed_domains = ['adams']
    start_urls = ['https://www.co.adams.il.us/Home/ShowDocument?id=4547']

    def parse(self, response):
        pass
