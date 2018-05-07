import os
from oslo_config import cfg
import unittest

from vmware_collector.common import opts


CUR_DIR = os.path.dirname(os.path.abspath(__file__))


class BaseTestCase(unittest.TestCase):
    conf_name = 'test.conf'

    def setUp(self):
        self.conf = cfg.ConfigOpts()
        opts.register_opts(self.conf)
        self.conf(['--config-file', os.path.join(CUR_DIR, self.conf_name)])
