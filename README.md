# aws-storage-benchmark
Tools for performing automated benchmarks of AWS storage systems


```
#!/bin/bash
yum update -y
yum install fio -y
yum install git -y 
yum install xfsprogs -y
pip install elasticsearch
git clone https://github.com/neoxia/aws-storage-benchmark.git
python /aws-storage-benchmark/test.py
```

Creating the index
```
curl -XDELETE 'http://localhost:9200/benchmark/'
curl -XPUT 'http://localhost:9200/benchmark'
curl -XPUT 'http://localhost:9200/benchmark/_mapping/metric/' -d '{"properties" : {meta: {properties:{"instance-id" : {"type" :"string", "index":"not_analyzed"}}}}}}'
curl -XPUT 'http://localhost:9200/benchmark/_mapping/metric/' -d '{"properties" : {meta: {properties:{"instance-type" : {"type" :"string", "index":"not_analyzed"}}}}}}'
```
