from inmates.scraper.spiders.macon import MaconRoster


class TestMaconRoster(MaconRoster):
    name = 'testing'
    urls = [
        'file:///Users/withtwoemms/programming/python/inmates/commissary/macon.html'
    ]
    # def start_requests(self):
    #     return super().start_requests()
    # def parse(self):
    #     return super().parse()

