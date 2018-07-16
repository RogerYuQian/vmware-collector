#!/usr/bin/env python2

# get all instance
# query from vmware
# push statics to mq

import collections
import datetime
import eventlet
import sys
import tenacity
import threading
import time
import tooz

from eventlet import greenpool
from eventlet import greenthread
from futurist import periodics
from oslo_config import cfg
from oslo_log import log
from tooz import coordination

from vmware_collector.common import opts
from vmware_collector.common import utils
from vmware_collector.services import gnocchi
from vmware_collector.services import nova
from vmware_collector.services import vmware
from vmware_collector.sync import service as sync


LOG = log.getLogger(__name__)
eventlet.monkey_patch(all=True, os=False, select=False,
                      socket=False, thread=True, time=False)


class VmScheduler(object):
    GROUP_ID = "vmware_collector"

    def __init__(self, conf, manager):
        self.conf = conf
        self.manager = manager
        self.sync_rate = conf.coordination.sync_rate
        self.index = 0
        self.members_num = 1
        if conf.coordination.backend_url is not None:
            self.coordinator, self.current_id = (
                utils.get_coordinator_and_start(conf.coordination.backend_url))
        else:
            # NOTE(rogeryu): If the conf.coordination.backend_url is not,
            # configured, it is necessary to ensure that the process can
            # proceed smoothly.
            LOG.warning("Connrdination's backend_url is not configured"
                        " and cannot collect data from multiple processes")
            self.current_id = utils.current_id()

    def _get_vm_sch_mobjs(self, current_index, members_num):
        """Get vms and distribute them evenly"""
        vm_mobjs = []
        instances_id = []
        instances = nova.get_all_instances(self.conf)

        def _allocate_instances(instances, member_index, members_num):
            """According to the number generated by uuid, the remainder
            with members_num is taken as the instance's location
            """
            results = []
            for ins_index, instance in enumerate(utils.group(instances, 1)):
                int_value = utils.uuid2int(instance[0].id)
                data_index = int_value % members_num
                if member_index == data_index:
                    results.append(instances[ins_index])
            return results

        instances = _allocate_instances(instances, current_index, members_num)
        for instance in instances:
            vm_mobj = self.manager.insp.get_vm_mobj(instance.id)
            if not vm_mobj:
                continue
            vm_power_stat = self.manager.insp.query_vm_property(
                vm_mobj, 'runtime.powerState')
            if vm_power_stat == 'poweredOff':
                LOG.debug('VM %s power state is off', vm_mobj)
                continue
            vm_mobjs.append(vm_mobj)
            instances_id.append(instance.id)

        LOG.info('The member: %s update vm_objs to %s',
                 self.current_id,
                 [(vm.value, instance_id) for vm, instance_id in
                  zip(vm_mobjs, instances_id)])
        return vm_mobjs

    # There are three ways to trigger
    # 1. Active trigger when the current member joins
    # 2. Passive trigger when there is a member in or out
    def _allocation_block(self, event):
        """Get member index and quantity"""
        get_members_req = self.coordinator.get_members(self.GROUP_ID)
        try:
            members = sorted(get_members_req.get())
            self.index = members.index(self.current_id)
            self.members_num = len(members)

            self.manager.get_vm_mobjs()
            LOG.info('Now member: %(id)s is working on block: %(block)s',
                     {'id': self.current_id,
                      'block': self.index})
        except Exception as e:
            LOG.error('Error when filtering instances, the '
                      'reason is : %s ', e)

    @utils.retry
    def configure(self):
        """Configure group management"""
        try:
            join_req = self.coordinator.join_group(self.GROUP_ID)
            join_req.get()
            LOG.info('Joined coordination group: %s', self.GROUP_ID)
            # Wait a period of sync_rate time
            LOG.info('A certain collector is kept for a period '
                     'of time to ensure that it is discovered by '
                     'other collectors')
            time.sleep(self.sync_rate)

            # Active trigger when the current member joins
            self._allocation_block(None)

            @periodics.periodic(spacing=self.sync_rate, run_immediately=True)
            def run_watchers():
                self.coordinator.run_watchers()

            self.periodic = periodics.PeriodicWorker.create([])
            self.periodic.add(run_watchers)
            t = threading.Thread(target=self.periodic.start)
            t.daemon = True
            t.start()

            # Passive trigger when there is a member in or out
            self.coordinator.watch_join_group(
                self.GROUP_ID, self._allocation_block)
            self.coordinator.watch_leave_group(
                self.GROUP_ID, self._allocation_block)

        except coordination.GroupNotCreated as e:
            create_group_req = self.coordinator.create_group(self.GROUP_ID)
            try:
                create_group_req.get()
            except coordination.GroupAlreadyExist:
                pass
            raise tenacity.TryAgain(e)
        except tooz.NotImplemented:
            LOG.warning('Configured coordination driver does not support '
                        'required functionality. Coordination is disabled.')
        except Exception as e:
            LOG.error('Failed to configure coordination. Coordination is '
                      'disabled: %s', e)

    def provide_fresh_vm_mobjs(self):
        """Provide updated vms"""
        if self.members_num == 0:
            LOG.error('There was a problem with the configure operation.'
                      ' No members joined the group, Please contact the'
                      ' administrator to handle this issue')
            raise
        else:
            return self._get_vm_sch_mobjs(self.index, self.members_num)


class Manager(object):
    def __init__(self, conf):
        self.conf = conf
        self.gnocchi_helper = gnocchi.get_gnocchi_helper(conf)
        LOG.info("Initializing inspector.")
        self.insp = vmware.VsphereInspector(conf)
        LOG.info("Inspector is initialized.")
        self.vm_mobjs = []
        self.vm_scheduler = VmScheduler(conf, self)
        if conf.coordination.backend_url is not None:
            self.vm_scheduler.configure()
        self.sync_manager = sync.SyncManager(conf)
        self._sync_run()

        greenthread.spawn(self._get_vm_mobjs)

    def _sync_run(self):
        @periodics.periodic(
            spacing=self.conf.vm_cache_period, run_immediately=True)
        def syncing():
            self.sync_manager.sync()

        periodic = periodics.PeriodicWorker.create([])
        periodic.add(syncing)
        t = threading.Thread(target=periodic.start)
        t.daemon = True
        t.start()

    def get_vm_mobjs(self):
        self.vm_mobjs[:] = self.vm_scheduler.provide_fresh_vm_mobjs()

    # TODO Add function to update vm list according to create_action
    def _get_vm_mobjs(self):
        while True:
            self.get_vm_mobjs()
            LOG.debug("VMs collected, waitting for the next period: %ss to "
                      "get vm data", self.conf.vm_cache_period)
            greenthread.sleep(self.conf.vm_cache_period)

    def query_vm_perf_stats(self, vm_mobjs):
        pool = greenpool.GreenPool(self.conf.pool_size)
        rets = []
        stats = []
        LOG.debug("The current vm_num is: %s, pool_size is: %s",
                  self.conf.vm_num, self.conf.pool_size)
        for sub_vms in utils.group(vm_mobjs, self.conf.vm_num):
            ret = pool.spawn(self.insp._query_vm_perf_stats,
                             sub_vms,
                             self.conf.interval)
            rets.append(ret)
        for r in rets:
            stats.extend(r.wait())
        return stats

    def _convert_metric_to_measure(self, metrics):
        '''
            [
                {'memory_usage': [{
                    'timestamp': '2018-xx',
                    'value': 75776.0
                    }]
                },
                {'cpu_util': [{
                    'timestamp': '2018-xx',
                    'value': 0.07
                    }]
                }
            ]

            to

            {
                83a600b8-68cd-4a17-8e67-62ec0a5ed25f: {
                    'memory_usage': [{
                        'timestamp': '2018-xx',
                        'value': 75776.0
                    }],
                    'cpu_util': [{
                        'timestamp': '2018-xx',
                        'value': 0.07
                    }]
                }
            }
        '''

        measures = collections.defaultdict(dict)
        for metric in metrics:
            resource = self.gnocchi_helper.get_resource(metric)
            measures[resource['id']].update(metric.to_metric())
        return measures

    def run_once(self):
        LOG.info('Starting to pull metrics in member: %s',
                 self.vm_scheduler.current_id)
        stats = self.query_vm_perf_stats(self.vm_mobjs)
        LOG.debug("Get stats: %s in member: %s",
                  [m.to_metric() for m in stats], self.vm_scheduler.current_id)
        measures = self._convert_metric_to_measure(stats)
        LOG.debug('Trying to push measures: %s in member: %s',
                  measures, self.vm_scheduler.current_id)
        self.gnocchi_helper.client.metric.batch_resources_metrics_measures(
            measures, create_metrics=True)
        LOG.info("All measures are pushed in member: %s",
                 self.vm_scheduler.current_id)

    def run(self):
        while True:
            start = utils.now()
            try:
                if not self.vm_mobjs:
                    LOG.info('No vm in member: %s is found. sleep 10 seconds.',
                             self.vm_scheduler.current_id)
                    greenthread.sleep(10)
                    continue
                self.run_once()
            except KeyboardInterrupt:
                LOG.info('Exiting')
                break
            except Exception:
                LOG.exception('Unkonw exception: %s')

            end = utils.now()
            period = end - start
            LOG.info('Get all metrics in member: %s in %s seconds',
                     self.vm_scheduler.current_id, period.total_seconds())
            next_run = start + datetime.timedelta(
                seconds=self.conf.interval)
            time_left = next_run - end
            if time_left.total_seconds() > 0:
                LOG.info('Sleep %s seconds to run next cycle in member: %s',
                         time_left.total_seconds(),
                         self.vm_scheduler.current_id)
                greenthread.sleep(time_left.total_seconds())
            else:
                LOG.warning(('it takes too long to pull metrics then'
                             ' interval, try to increase the interval'
                             ' options in member: %s'),
                            self.vm_scheduler.current_id)
                greenthread.sleep(10)


def main():
    conf = cfg.ConfigOpts()
    opts.register_opts(conf)
    log.register_options(conf)
    log.set_defaults()
    conf(sys.argv[1:])
    log.setup(conf, 'vmware_collector')

    manager = Manager(conf)
    manager.run()


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    main()
