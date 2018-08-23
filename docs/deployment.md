# Deployment

This code include a ansible role to deploy vmware_collector container. Here is how to use it

    git clone http://gitlab.sh.99cloud.net/99cloud/vmware_collector.git

    ln -s $(readlink -f vmware_collector/vmware_collector_role) /etc/ansible/roles/

    # The <kolla-ansible> directory is usually under '/usr/share/', you can search by the 'find' command
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

Deploy multiple vmware_collector processes

**Note:**
    vmware_collector supports member groups, allowing multiple processes to run at the same time, and the collected content is fragmented according to the number of members.
    You can run multiple processes on a single node, or run one process per node. Since it is now deployed through kolla-ansible, Recommend each node to initiate an acquisition process.
    The above modification about the inventory file is to deploy a vmware_collector process on each control node. If you want to deploy on the compute node or other nodes, add the corresponding:

    cat <<EOF >> multinode
    [vmware_collector:children]
    control
    compute
    storage
    EOF

# Animbus

Animbus support vmware_collector since 6.3, the roles and inventory file is already added. If you wanna
enabled it, just enable it in `globals.yml` and then deploy again.
