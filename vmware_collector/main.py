#!/usr/bin/env python2

# get all instance
# query from vmware
# push statics to mq

import sys
import logging
import time
import threading
import datetime

from eventlet import greenpool
from oslo_config import cfg

from vmware_collector import opts
from vmware_collector import nova
from vmware_collector import vmware
from vmware_collector import objects
from vmware_collector import utils
from vmware_collector import gnocchi


LOG = logging.getLogger(__name__)


class Manager(object):
    def __init__(self, conf):
        self.conf = conf
        self.novaclient = nova.get_nova_client(conf)
        self.gnocchi_helper = gnocchi.get_gnocchi_helper(conf)
        LOG.info("Initializing inspector.")
        self.insp = vmware.VsphereInspector(self.conf)
        LOG.info("Inspector is initialized.")
        self.vm_mobjs = []
        update_thread = threading.Thread(target=self.get_vm_mobjs)
        update_thread.daemon = True
        update_thread.start()

    def get_all_nova_instance(self):
        return self.novaclient.servers.list()

    def get_vm_mobjs(self):
        while True:
            vm_mobjs = []
            for instance in self.get_all_nova_instance():
                vm_mobj = self.insp.get_vm_mobj(instance.id)
                if not vm_mobj:
                    continue
                vm_power_stat = self.insp.query_vm_property(
                    vm_mobj, 'runtime.powerState')
                if vm_power_stat == 'poweredOff':
                    LOG.debug('VM %s power state is off', vm_mobj)
                    continue
                vm_mobjs.append(vm_mobj)
            LOG.info('Update vm_objs to %s', vm_mobjs)
            # TODO add lock
            self.vm_mobjs[:] = vm_mobjs
            time.sleep(self.conf.vm_cache_period)

    def query_vm_perf_stats(self, vm_mobjs):
        pool = greenpool.GreenPool(self.conf.pool_size)
        rets = []
        stats = {}
        for sub_vms in utils.group(vm_mobjs, self.conf.vm_num):
            ret = pool.spawn(self.insp._query_vm_perf_stats,
                             sub_vms,
                             self.conf.interval)
            rets.append(ret)
        for r in rets:
            stats.update(r.wait())
        return stats

    def run_once(self):
        LOG.info('Starting to pull metrics')
        stats = self.query_vm_perf_stats(self.vm_mobjs)
        measures = {}
        LOG.info("Get stats: %s", stats)
        for instance_id, props in stats.items():
            for stat in objects.factory(self.conf, instance_id, props):
                measures.update(stat.to_metric())
        LOG.debug('Trying to push measures: %s', measures)
        self.gnocchi_helper.client.metric.batch_resources_metrics_measures(
            measures, create_metrics=True)
        LOG.info("All measures are pushed")

    def run(self):
        while True:
            try:
                if not self.vm_mobjs:
                    LOG.info('No vm is found. sleep 10 seconds.')
                    time.sleep(10)
                    continue
                start = utils.now()
                self.run_once()
                end = utils.now()
                period = end - start
                LOG.info('Get all metrics in %s seconds',
                         period.total_seconds())
                next_run = start + datetime.timedelta(
                        seconds=self.conf.interval)
                time_left = next_run - end
                if time_left.total_seconds() > 0:
                    LOG.info('Sleep %s seconds to run next cycle',
                             time_left.total_seconds())
                    time.sleep(time_left.total_seconds())
                else:
                    LOG.warning(('it takes too long to pull metrics then'
                                 ' interval, try to increase the interval'
                                 ' options'))
                    time.sleep(10)
            except KeyboardInterrupt:
                LOG.info('Exiting')
                break
            except Exception:
                LOG.exception('Unkonw exception: %s')


def main():
    conf = cfg.ConfigOpts()
    opts.register_opts(conf)
    conf(sys.argv[1:])
    manager = Manager(conf)
    logging.basicConfig(level=logging.INFO)
    manager.run()


if __name__ == "__main__":
    main()
