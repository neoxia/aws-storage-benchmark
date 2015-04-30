import boto.ec2
import boto.utils
import requests
import time
from datetime import datetime
from elasticsearch import Elasticsearch

r = requests.get('http://169.254.169.254/latest/meta-data/placement/availability-zone/')
print r.text


conn = boto.ec2.connect_to_region(r.text[:-1])

print (conn)

meta = boto.utils.get_instance_metadata()

print (meta['block-device-mapping'])

volumes = conn.get_all_volumes(filters={'attachment.instance-id': meta['instance-id']})

print (volumes)

doc = {'meta' : meta }

es = Elasticsearch(['local.elasticsearch.sudomakeinstall.me:9200']) #elasticsearch.sudomakeinstall.me'})

doc["creation-date"] = datetime.now()#.strftime("%Y-%m-%dT%H:%M:%SZ")


for volume in volumes :
	doc['volume'] = {'volume_id' : str(volume.id), 'volume_size' : str(volume.size), 'volume_zone' : str(volume.zone), 'volume_type' : str(volume.type), 'volume_iops' : str(volume.iops), 'volume_encrypted' : str(volume.encrypted)}	
	res = es.index(index='benchmark', doc_type='metric', id="",  body=doc)
