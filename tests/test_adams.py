from unittest import TestCase

from fixtures import fixture_paths
from fixtures import jsonfrom


class AdamsRosterTest(TestCase):

    fixtures = jsonfrom(fixture_paths['adams.json'].read_bytes())
    assert isinstance(fixtures, list) == True

    def test_adams(self):
        inmates_attributes = [struct.keys() for struct in self.fixtures]
        expected_attributes = [
            'Gender',
            'Height',
            'HousingFacility',
            'InCustody',
            'MultipleBookings',
            'Name',
            'Race',
            'Weight',
        ]
        for inmate_attributes in inmates_attributes:
            self.assertCountEqual(inmate_attributes, expected_attributes)

