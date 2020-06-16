from inmates.scraper.spiders.macon import MaconRoster


class TestMaconRoster(MaconRoster):
    name = 'test-macon'
    urls = [
        'file:///Users/withtwoemms/programming/python/inmates/commissary/macon.html'
    ]

