## vmware_collector features

* [Multi checkers](#checkers)
* [Multi actions](#actions)
* [Support cold backup nodes](#cold-backup-nodes)

## Common Configuration Interpretation

    Get more configuration item information Please refer to the common/opts.py file, \
    where have relevant explanation

## Key Configuration Parameters

    [DEFAULT]
    # The period of collecting resource data from vmware
    interval = 60

    # The period of obtaining virtual machine list information from nova
    vm_cache_period = 600

    # Collected data item
    metrics = cpu,ram,network_tx,network_rx,disk_read,disk_write,disk_read_iops,disk_write_iops

    # Soft/hard delete option
    #   - Set `false` to soft delete: the resource and corresponding data are not deleted,
    #     and the resource's `end_at` will be filled when a soft delete operation occurs.
    #   - Set `true` to hard delete: the resource and corresponding data are deleted
    hard_delete = false

## Simple Usage

configure `/etc/vmware_collector/vmware_collector.conf`

    [DEFAULT]
    interval=60
    log_dir = /var/log/vmware_collector

    metrics=cpu,ram,network_tx,network_rx,disk_read,disk_write,disk_read_iops,disk_write_iops

    [vmware]
    host_ip=192.168.22.171
    host_port=443
    host_username=administrator@vsphere.local
    host_password=99Cloud!@#
    insecure = True

    [keystone_authtoken]
    auth_type=password
    auth_url=http://172.18.22.215:35357/v3
    project_name=admin
    project_domain_name=Default
    username=admin
    user_domain_name=Default
    password=P91MoSOBi1ayhp7vhvnVeMiHGGmWhZxxgSuyfNwf

Start the service

    vmware_collector --config-file /etc/vmware_collector/vmware_collector.conf

## Full Configuration

    [DEFAULT]
    interval=60
    log_dir = /var/log/vmware_collector
    vm_cache_period=600
    metrics=cpu,ram,network_tx,network_rx,disk_read,disk_write,disk_read_iops,disk_write_iops
    hard_delete=False

    [vmware]
    host_ip=192.168.22.171
    host_port=443
    host_username=administrator@vsphere.local
    host_password=99Cloud!@#
    insecure = True

    [keystone_authtoken]
    auth_type=password
    auth_url=http://172.18.22.215:35357/v3
    project_name=admin
    project_domain_name=Default
    username=admin
    user_domain_name=Default
    password=P91MoSOBi1ayhp7vhvnVeMiHGGmWhZxxgSuyfNwf

    [coordination]
    backend_url = memcached://172.18.22.212:11211
