import datetime
import json
from vmware_collector import utils
from vmware_collector.tests import base


class DatetimeEncoderTest(base.BaseTestCase):

    def test_date(self):
        data = datetime.datetime(2018, 5, 6, 10, 0, 7)
        real = json.dumps(data, cls=utils.DatetimeEncoder)
        self.assertEqual('"2018-05-06T10:00:07"', real)
