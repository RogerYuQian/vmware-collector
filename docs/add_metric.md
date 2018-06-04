# 添加新的监控项
## 1.监控项代码
**目录位置**
vmware_collector/metrics.py
**主要内容**
1. 定义新metric的conter_name；
2. 新增Metric类继承BaseMetric类；
3. 实现handle_result以获取measures

## 2.添加entry_points
**目录位置**
setup.cfg
**主要内容**
参考[entry_points]中的vmware_collector.metrics段中内容，仿照其他已有metric项新增监控项及路径

## 3.修改配置项
**主要内容**
修改配置文件vmware_collecot.conf中的[DEFAULT]内metrics段：

```
metrics = cpu, ram, network_tx, network_rx, disk_read, disk_write
```
上述为已有监控项，对应名称与entry_points中相对应
