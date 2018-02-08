from vmware_collector.tests import base as base_test
from vmware_collector import exceptions


class CollectorExceptionTest(base_test.BaseTestCase):

    def test_message(self):

        ce = exceptions.CollectorException(message='hello')
        self.assertEqual('hello', ce.format_message())

    def test_msg_fmt(self):
        class SubException(exceptions.CollectorException):
            msg_fmt = 'hello %(name)s'

        ce = SubException(name='jeffrey')
        self.assertEqual('hello jeffrey', ce.format_message())

    def test_log_exception(self):
        ce = exceptions.CollectorException(message='hello')
        self.assertEqual('hello', ce.format_message())
