# aws-storage-benchmark
Tools for performing automated benchmarks of AWS storage systems


```
#!/bin/bash
yum update -y
yum install fio -y
yum install git -y 
pip install elasticsearch
git clone https://github.com/neoxia/aws-storage-benchmark.git
python /aws-storage-benchmark/test.py
```
