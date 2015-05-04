import boto.ec2
import boto.utils
import requests
import json
import sys

from datetime import datetime
from elasticsearch import Elasticsearch
from subprocess import PIPE, Popen

AZ_ENDPOINT = 'http://169.254.169.254/latest/meta-data/placement/availability-zone/'
ES_ADDR = 'local.elasticsearch.sudomakeinstall.me:9200'

es = Elasticsearch([ES_ADDR])

def get_region():
    r = requests.get(AZ_ENDPOINT)
    az = r.text
    return az[:-1]

def run(cmd):
    return Popen(str(cmd).split(), stdout=PIPE, stderr=PIPE)

def log(text, severity='INFO'):
    #Dummy log
    color = {}
    color['INFO'] = '\033[94m'
    color['WARNING'] = '\033[93m'
    color['ERROR'] = '\033[91m'
    color['ENDC'] = '\033[0m'

    print('[%s][%s%s%s] %s' % (sys.argv[0], color[severity] ,severity, color['ENDC'], text))
    

conn = boto.ec2.connect_to_region(get_region())
meta = boto.utils.get_instance_metadata()
volumes = conn.get_all_volumes(filters={'attachment.instance-id': meta['instance-id']})

log('Initialize JSON document')
doc = {'meta' : meta }
doc["creation-date"] = datetime.now()


for volume in volumes :
    log('Test %s' % volume.id)
    try : 
        log('EXT4 Format volume')
        cmd = "mkfs.ext4 -F %s" % volume.attach_data.device
        retcode = run(cmd).wait()
        if (retcode) :
            raise Exception

        log('Mount volume')
        cmd = "mount %s /mnt" % volume.attach_data.device
        retcode = run(cmd).wait()
        if (retcode) :
            raise Exception

        log('Testing volume')
        cmd = "fio --directory=/mnt --size=1M --output-format=json --name %s " % volume.id
        proc = run(cmd)
        retcode = proc.wait()
        if (retcode) : 
            raise Exception 
            

        log('Send test metrics at %s' % ES_ADDR)
        fio_result = json.loads(proc.stdout.read())
        for job_result in fio_result['jobs'] :
            doc['result'] = job_result 
            doc['volume'] = {
                'volume_id' : str(volume.id), 
                'volume_attach_device' : volume.attach_data.device, 
                'volume_size' : str(volume.size), 
                'volume_zone' : str(volume.zone), 
                'volume_type' : str(volume.type), 
                'volume_fs' : 'ext4',
                'volume_iops' : str(volume.iops),
                'volume_encrypted' : str(volume.encrypted)
            }    
            res = es.index(index='benchmark', doc_type='metric', id="",  body=doc)

    except Exception as e :
        log('Volume %s failed %s' % (volume.id ,str(e)), 'ERROR')

    finally :
        log('Umount filesystem')
        run('umount /mnt').wait()
