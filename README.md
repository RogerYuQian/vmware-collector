# 安装方法 

    # 安装依赖
    pip install -r requirements.txt

    # 修改变量 main.py 里面的 NODE 变量

    # 运行脚本

    python main.py | tee -a test.log

# 说明

这个测试脚本通过是几种数据采集方式，来得到数据采集的性能数据

采集方式包括：

- 一台一台虚拟机的采集
- 一下拿到所有的虚拟机的数据
- 通过多线程，每个线程拿一部分虚拟机的数据

# How to use

Install this package and requirements

    pip install vmware_collect
    pip install -r requirements.txt

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
