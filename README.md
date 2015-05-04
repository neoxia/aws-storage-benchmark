# aws-storage-benchmark
Tools for performing automated benchmarks of AWS storage systems


```
#!/bin/bash
sudo yum update -y
sudo yum install fio -y
sudo yum install git -y 
sudo pip install elasticsearch
git clone https://github.com/neoxia/aws-storage-benchmark.git
sudo python aws-storage-benchmark/test.py
```
