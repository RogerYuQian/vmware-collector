#!/usr/bin/env python2

# get all instance
# query from vmware
# push statics to mq

import sys
import logging
import time

from oslo_config import cfg

from vmware_collector import opts
from vmware_collector import nova
from vmware_collector import vmware
from vmware_collector import gnocchi


LOG = logging.getLogger(__name__)


class Manager(object):

    def __init__(self, conf):
        self.conf = conf
        self.novaclient = nova.get_nova_client(conf)
        self.vmware_api = vmware.Vmware(conf)

    def get_all_nova_instance(self):
        return self.novaclient.servers.list()

    def run(self):
        # instances = self.get_all_nova_instance()
        # ids = [instance.id for instance in instances]
        # vmware_nodes = self.vmware_api.get_nodes_by_name(ids)
        vmware_nodes = self.vmware_api.get_all_power_on_nodes()
        nodes = list(vmware_nodes)
        instance_stats = self.vmware_api.get_counters(nodes)
        gh = gnocchi.GnocchiHelper(self.conf)
        gh.handler_instance_stats(instance_stats)


def main():
    conf = cfg.ConfigOpts()
    opts.register_opts(conf)
    conf(sys.argv[1:])
    manager = Manager(conf)
    logging.basicConfig(level=logging.INFO)
    while True:
        manager.run()
        time.sleep(10)


if __name__ == "__main__":
    main()
