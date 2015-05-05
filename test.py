#!/usr/bin/python
import sys
import os
import boto.ec2
import boto.utils
import requests
import json

from datetime import datetime
from elasticsearch import Elasticsearch
from subprocess import PIPE, Popen

if os.getuid():
    raise OSError('You must be root')


AZ_ENDPOINT = 'http://169.254.169.254/latest/meta-data/placement/availability-zone/'
ES_ADDR = 'local.elasticsearch.sudomakeinstall.me:9200'

es = Elasticsearch([ES_ADDR])

def get_region():
    r = requests.get(AZ_ENDPOINT)
    az = r.text
    return az[:-1]

def run(cmd):
    return Popen(str(cmd).split(), stdout=PIPE, stderr=PIPE)

def log(text, severity = 'INFO', volume = None):
    #Dummy log
    color = {}
    color['INFO'] = '\033[94m'
    color['WARNING'] = '\033[93m'
    color['ERROR'] = '\033[91m'
    color['ENDC'] = '\033[0m'

    print('[%s][%s%s%s] %s' % (sys.argv[0], color[severity] ,severity, color['ENDC'], text))
    
    # Send log to elasticsearch
    log = {}
    log['date'] = datetime.now()
    log['severity'] = severity
    log['instance-id'] = meta['instance-id']
    log['instance-type'] = meta['instance-type']
    log['message'] = text
    log['volume-id'] = volume
    res = es.index(index='logs', doc_type='log', id="",  body=log)

conn = boto.ec2.connect_to_region(get_region())
meta = boto.utils.get_instance_metadata()
volumes = conn.get_all_volumes(filters={'attachment.instance-id': meta['instance-id']})

log('Initialize JSON document')
doc = {'meta' : meta }

fstype = ['ext4 -F', 'xfs -f']
blocksize = ['4k', '32k', '512k', '1M']


for metakey in meta['block-device-mapping'].keys():
    if 'ephemeral' in metakey:
        fakevolume = boto.ec2.volume.Volume()
        fakevolume.attach_data = boto.ec2.volume.AttachmentSet()

        #Vol
        fakevolume.id = metakey
        fakevolume.size = "0"
        fakevolume.attach_data.device = "/dev/%s" % meta['block-device-mapping'][metakey]
        fakevolume.zone = requests.get(AZ_ENDPOINT).text
        fakevolume.type = 'instance-store'
        fakevolume.iops = -1
        fakevolume.encrypted = False

        volumes.append(fakevolume)

for volume in volumes :
    if meta['block-device-mapping']['root'] != volume.attach_data.device:
        for fs in fstype:
            for bs in blocksize:
                log('Test %s' % volume.id)
                try : 
                    log('%s Format volume' % fs[:-3])
                    cmd = "mkfs.%s %s" % (fs, volume.attach_data.device)
                    retcode = run(cmd).wait()
                    if (retcode) :
                        raise OSError('Fail to format volume %s' % cmd)

                    log('Mount volume')
                    cmd = "mount %s /mnt" % volume.attach_data.device
                    retcode = run(cmd).wait()
                    if (retcode) :
                        raise OSError('Fail to mount volume')

                    log('Testing volume')
                    cmd = "fio --directory=/mnt --output-format=json --name %s --direct=1 --ioengine=libaio --refill_buffers --scramble_buffers=1 --blocksize=%s --rw=randrw --numjobs=1 --iodepth=64 --size=1G" % (volume.id, bs)
                    proc = run(cmd)
                    retcode = proc.wait()
                    if (retcode) : 
                        raise OSError('Fail exec fio test')
                        

                    log('Send test metrics at %s' % ES_ADDR)
                    fio_result = json.loads(proc.stdout.read())
                    for job_result in fio_result['jobs'] :
                        doc['result'] = job_result
                        doc['block-size'] = bs
                        doc['volume'] = {
                            'volume_id' : str(volume.id), 
                            'volume_attach_device' : volume.attach_data.device, 
                            'volume_size' : str(volume.size), 
                            'volume_zone' : str(volume.zone), 
                            'volume_type' : str(volume.type), 
                            'volume_fs' : fs[:-3], # delete option
                            'volume_iops' : str(volume.iops),
                            'volume_encrypted' : str(volume.encrypted)
                        }    

                        doc["creation-date"] = datetime.now()
                        res = es.index(index='benchmark', doc_type='metric', id="",  body=doc)

                except OSError as e :
                    log('%s' % e, 'ERROR', volume.id)

                finally :
                    log('Umount filesystem')
                    run('umount /mnt').wait()

conn.stop_instances(instance_ids=[meta['instance-id']])
