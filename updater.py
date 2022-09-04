from apscheduler.schedulers.background import BackgroundScheduler
from django.db.models import Count
from openstack.models import OpenstackInstance
import requests
import json


def update_something():
    import openstack_controller as oc                           #
    openstack_hostIP = oc.hostIP
    print("테이블 갯수", OpenstackInstance.objects.all().count())
    instance_count = OpenstackInstance.objects.all().count()
    if instance_count == 0:
        return print("instance 없음")
    token = oc.admin_token()
    print("a")
    #print(OpenstackInstance.objects.values('instance_id')[0]['instance_id'])
    for n in range(0, instance_count):
        backup_payload = {
            "createBackup": {
                "name": "Backup " + str(OpenstackInstance.objects.values('instance_id')[n]['instance_id']),
                "backup_type": "daily",
                "rotation": 1
            }
        }
        instance_info_req = requests.post("http://" + openstack_hostIP + "/compute/v2.1/servers/" + OpenstackInstance.objects.values('instance_id')[n]['instance_id'] + "/action",
                                     headers = {'X-Auth-Token': token},
                                     data = json.dumps(backup_payload))
        print(instance_info_req.headers["Location"])  # django orm에 저장  이미지 url 저장 !!
        ## freezer-agent 백업 코드 후 명령어에서 바뀌는 부분 들고 와야 됨 .


def update_something_2():
    print("b")





def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_something, 'interval', seconds=60)
    scheduler.start()

def start_2():
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_something_2, 'interval', seconds=60)
    scheduler.start()
