from unittest import TestCase

from fixtures import fixture_paths
from fixtures import jsonfrom


class InmatesScraperSpiderMaconTest(TestCase):

    fixtures = jsonfrom(fixture_paths['macon.json'].read_bytes())
    assert isinstance(fixtures, list) == True

    def test_macon(self):
        inmates_attributes = [struct.keys() for struct in self.fixtures]
        expected_attributes = ['Photo', 'Name', 'SubjectNumber', 'InCustody', 'ScheduledReleaseDate', 'Race', 'Gender', 'Height', 'Weight', 'MultipleBookings', 'HousingFacility']
        for inmate_attributes in inmates_attributes:
            self.assertCountEqual(inmate_attributes, expected_attributes)

