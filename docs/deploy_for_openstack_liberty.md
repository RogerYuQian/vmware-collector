This is deployment for China Telecom's OpenStack Liberty integrate. Kolla pike
will be deployed and integrate with the OpenStack.

# Prerequisite

- ensure the clock on all nodes are synchronized
- kolla pike image
  - redis, gnocchi-\*, aodh-\*, cron, kolla\_toolbox, fluentd
- kolla-ansible pike source code
- vmware\_collector source code and image

# Install setps

## prepare gnocchi account and endpoint

```bash
# create service and endpoint for gnocchi & aodh
gnocchi_url=http://192.168.122.6:8041
aodh_url=http://192.168.122.6:8042

openstack service create --name gnocchi metric
openstack service create --name aodh alarming

gnocchi_service_id=$(openstack service list -f value | grep gnocchi | awk '{print $1}')
aodh_service_id=$(openstack service list -f value | grep aodh | awk '{print $1}')
openstack endpoint create \
	--publicurl $gnocchi_url \
    --adminurl $gnocchi_url \
    --internal $gnocchi_url \
    --region RegionOne \
    $gnocchi_service_id
openstack endpoint create \
	--publicurl $aodh_url \
    --adminurl $aodh_url \
    --internal $aodh_url \
    --region RegionOne \
    $aodh_service_id

iptables -I INPUT 1 -p tcp --dport 8041 -j ACCEPT
iptables -I INPUT 1 -p tcp --dport 8042 -j ACCEPT

# create user
project_service_id=$(openstack project list  -f value | awk '/services/{print $1}')

openstack user create \
	--password {gnocchi_passwd} \
    --project $project_service_id \
    --enable gnocchi
openstack user create \
	--password {aodh_passwd} \
    --project $project_service_id \
    --enable aodh

openstack role add --project services --user gnocchi admin
openstack role add --project services --user aodh admin
```

## Install kolla-ansible in virtualenv

    pip install virtualenv
    virtualenv /opt/kolla
    source /opt/kolla/bin/activate
    cd <<path to kolla-ansible>>
    pip install .

## prepare configuration

    mkdir -p /etc/kolla
    cp etc/globals.yml etc/password.yml /etc/kolla

fix the globals according

    # /etc/kolla/globals.yml
    vmware_vcenter_host_ip: 192.168.53.207
    vmware_vcenter_host_port: 443
    vmware_vcenter_host_username: administrator@vsphere.local
    vmware_vcenter_host_password: P@ssw0rd
    vmware_vcenter_insecure: "True"

    network_interface: br-mgmt
    kolla_internal_vip_address: 192.168.122.2
    database_address: 192.168.122.2
    # database_port:
    database_user: root

    enable_gnocchi: yes
    enable_redis: yes

Fix the passwords according

    #/etc/kolla/globals.yml
    database_password: yyyy
    nova_keystone_password: xxx

Fix openstack configuration according

    #/etc/kolla/config/global.conf
    [keystone_authtoken]
    project_name = services
    memcache_security_strategy = None
    memcached_servers = 192.168.122.3:11211,192.168.122.4:11211,192.168.122.5:11211

create ceph related resource for gnocchi

    # create gnocchi pool and keys
    rados mkpool gnocchi
    ceph auth get-or-create client.gnocchi \
        mon 'allow r' \
        osd 'allow class-read object_prefix rbd_children, allow rwx pool=gnocchi' \
        > ceph.client.gnocchi.keyring

copy ceph related resource into gnocchi custom resource

    mkdir -p /etc/kolla/config/gnocchi
    cp ceph.conf ceph.client.gnocchi.keyring\
        /etc/kolla/config/gnocchi/

Make sure rabbitmq has the 'openstack' user, if not, create it and empowerment. Aodh will use

    rabbitmqctl list_users | grep openstack
    rabbitmqctl add_user openstack {openstack_passwd}
    rabbitmqctl set_permissions -p / openstack '.*' '.*' '.*'

# deploy

    kolla-ansible deploy -t redis,gnocchi,aodh

> deploy vmware-collector, please check [deployment](deployment.md)

# others may be useful

```sql
grant all on *.* to 'root'@'%' identified by 'admin' with grant option;
```
