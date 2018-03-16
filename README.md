# How to use

Install this package and requirements

    tar xvf vmware_collector-*.tar.gz
    cd vmware_collector
    pip install -c upper-constraints.txt .

configure `/etc/vmware_collector/vmware_collector.conf` file

    [DEFAULT]
    interval=10

    [vmware]
    host_ip=192.168.22.171
    host_port=443
    host_username=administrator@vsphere.local
    host_password=xxxx
    insecure = True

    [keystone_authtoken]
    auth_type=password
    auth_url=http://172.18.22.215:35357/v3
    project_name=admin
    project_domain_name=Default
    username=admin
    user_domain_name=Default
    password=yyyy

run add script or service

    vmware-collector --config-file /etc/vmware_collector/vmware_collector 

## 架构

### Ceilometer 的问题

ceilometer 在采集数据的时候，是拿到所有的需要采集的虚拟机，然后对每个虚拟机的每
个 metric 单独发请求来采集数据。在使用 libvirt 时，这种架构是没有问题的。因为这
些数据来自于当前计算节点的 libvirt 这个数据量并不大，对 libvirt 也不会造成压力。

在使用 vmware 时，情况就不一样了。因为所有的数据采集必须要请求中央的 vsphere 节
点，这就产生了大量的 api 请求，对 vsphere 产生了很大的压力，监控节很难做的更细
的粒度。

### 优化架构

由于 ceilometer 的架构很难调整，直接重新写了当前这么一个工具。

原理是：采集数据时，vphere 的 api 是支持批量采集的。可以同时采集不同虚拟机的，
不同监控数据点。这样一个请求就能拿到大量所需要数据。同时，vshpere 自身也有一个
每次 api 调用所返回的最大 metric 个数，所以不能一个请求拿到所有的虚拟机

基于上，该工具的实现如下

- 使用一个协程池来处理监控数据采集，池的大小及每次采集的虚拟机个数可能通过
  配置文件调整。同时采集周期默认是 60 秒。
- 用另外一个协程来同步需要采集的虚拟机ID, 默认是 600 秒同步一次，可以有效的降低
  api 调用次数。
- 本工具直接很入了 gnocchi-api , 没有通过 ceilometer 的消息总线机制。原因是降低
  MQ 的开销，同时 gnocchi-api 的处理能力是很强大的，足以处理这些数据，没有必要
  经过 MQ 来缓存。
- 在写入 gnocchi-api 时， 使用了批量写入的 api , 可以一次调用，写入所有的数据

## TODO

- resource type 现在还要依赖 ceilometer-upgrade 来创建，可以在本工具中创建出来.
- 增加新的 vmware 监控点还是比较复杂的，可以优化下，弄成可以配置的。
