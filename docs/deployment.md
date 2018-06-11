# Deployment

This code include a ansible role to deploy vmware_collector container. Here is how to use it

    git clone http://gitlab.sh.99cloud.net/99cloud/vmware_collector.git

    ln -s $(readlink -f vmware_collector/vmware_collector_role) /etc/ansible/roles/

    cp /etc/ansible/roles/vmware_collector_role/vmware_collector.yml <kolla-ansible>/ansible/vmware_collector.yml

Add vmware_collector related groups into inventory files

    cat <<EOF >> multinode
    [vmware_collector:children]
    control
    EOF

Vmware_collector is disabled in default, add `enable_vmware_collector` in `globals.yml` file

    cat <<EOF >> /etc/kolla/globals.yml
    enable_vmware_collector: yes
    vmware_vcenter_host_ip: 192.168.53.207
    vmware_vcenter_host_port: 443
    vmware_vcenter_host_username: admin
    vmware_vcenter_host_password: password
    vmware_vcenter_insecure: "True"
    EOF

Then you could deploy by using

    kolla-ansible -i <multinode> -p <kolla-ansible>/ansible/vmware_collector.yml deploy

# Animbus

Animbus support vmware_collector since 6.3, the roles and inventory file is already added. If you wanna
enabled it, just enable it in `globals.yml` and then deploy again.
