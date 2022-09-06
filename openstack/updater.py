import json
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from openstack.models import OpenstackInstance

def update_something():
    print("this function runs every 10 seconds")
    import openstack_controller as oc                            # import는 여기 고정
    openstack_hostIP = oc.hostIP

    print("테이블 갯수", OpenstackInstance.objects.all().count())
    instance_count = OpenstackInstance.objects.all().count()
    if instance_count == 0:
        return print("instance 없음")


    token = oc.admin_token()
    print(OpenstackInstance.objects.values('instance_id')[0]['instance_id'])
    for n in range(0, instance_count):
        backup_payload = {
            "createBackup": {
                "name": "Backup " + str(OpenstackInstance.objects.values('instance_id')[n]['instance_id']),
                "backup_type": "daily",
                "rotation": 1
            }
        }
        instance_info_req = requests.post("http://" + openstack_hostIP + "/compute/v2.1/servers/" +
                                          OpenstackInstance.objects.values('instance_id')[n]['instance_id'] + "/action",
                                          headers={'X-Auth-Token': token},
                                          data=json.dumps(backup_payload))

        print(instance_info_req.headers["Location"])  # django orm에 저장  이미지 url 저장 !!
        image_URL = instance_info_req.headers["Location"]
        print("image_URL : " + image_URL)

        image_ID = image_URL.split("/")[6]
        print("image_ID : " + image_ID)

        file = open('C:/os_image/' + image_ID + '.qcow2', 'wb')
        file.write(instance_info_req.content)
        file.close()

        print("image file download response is", instance_info_req)

        #장고 fileboard에 post로 보내고 모델 추가!!




    # user_res = requests.get("http://192.168.56.128/image/v2/images/5484ea3c-aa0d-412e-9022-d8ff37ae5919/file",
    #                         headers = {"X-Auth-Token" : "gAAAAABjFwx-cyqDpX9o0cXJR_j6VPBbwWkS8L7gsK5xIjRESxGxNWAbbeJnMlg-SX9N1X4gL6_M-WjfFYPH4AW7VtrIrPkdvqeYCMNr2xZpp5KgTfhzlmexypLLTULHf9k0xZXRtlDG-d2F6BDwW4YDVxjBpRoTs8x2C-qPpCuMUTV5sr5nD2Q"}
    #                         )
    # file = open('C:/os_image/' + "5484ea3c-aa0d-412e-9022-d8ff37ae5919" + '.qcow2', 'wb')
    # file.write(user_res.content)
    # file.close()
    # print("download complete")

        #string = "http://192.168.56.128/compute/v2.1/images/5484ea3c-aa0d-412e-9022-d8ff37ae5919"
        #print(string.split("/")[6])
        #이미지 url
        ## freezer-agent 백업 코드 후 명령어에서 바뀌는 부분 들고 와야 됨 .





def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_something, 'interval', seconds=30)
    scheduler.start()
