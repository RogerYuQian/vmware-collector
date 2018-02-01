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
from vmware_collector import objects
from vmware_collector import gnocchi

LOG = logging.getLogger(__name__)


class Manager(object):
    def __init__(self, conf):
        self.conf = conf
        self.novaclient = nova.get_nova_client(conf)
        self.gnocchi_helper = gnocchi.get_gnocchi_helper(conf)
        self.insp = vmware.VsphereInspector(self.conf)

    def get_all_nova_instance(self):
        return self.novaclient.servers.list()

    def get_vm_mobjs(self):
        for instance in self.get_all_nova_instance():
            vm_mobj = self.insp.get_vm_mobj(instance.id)
            if vm_mobj:
                yield vm_mobj

    def run(self):
        vm_mobjs = list(self.get_vm_mobjs())
        LOG.info('Get vm objects from vmware: %s', vm_mobjs)
        # TODO(jeffrey4l): make this parallel
        stats = self.insp._query_vm_perf_stats(vm_mobjs, 60)
        measures = {}
        LOG.info("Get stats: %s", stats)
        for instance_id, props in stats.items():
            for stat in objects.factory(self.conf, instance_id, props):
                measures.update(stat.to_metric())
        LOG.debug('Trying to push measures: %s', measures)
        self.gnocchi_helper.client.metric.batch_resources_metrics_measures(
            measures, create_metrics=True)


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
