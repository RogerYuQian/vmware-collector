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
