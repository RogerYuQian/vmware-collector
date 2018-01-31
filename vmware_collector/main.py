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

    def get_all_nova_instance(self):
        return self.novaclient.servers.list()

    def run(self):
        insp = vmware.VsphereInspector(self.conf)
        insp._init_vm_mobj_lookup_map()

        vm_mobjs = insp._vm_mobj_lookup_map.values()

        stats = insp._query_vm_perf_stats(vm_mobjs, 60)
        gh = gnocchi.GnocchiHelper(self.conf)
        gh.handler_instance_stats(stats)


def main():
    conf = cfg.ConfigOpts()
    opts.register_opts(conf)
    conf(sys.argv[1:])
    manager = Manager(conf)
    logging.basicConfig(level=logging.INFO)
    while True:
        manager.run()
        break
        time.sleep(10)


if __name__ == "__main__":
    main()
