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
