import json
from re import S
import time
from sqlite3 import OperationalError
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from openstack.models import OpenstackBackupImage, OpenstackInstance
from openstack.serializers import OpenstackBackupImageSerializer
from fileBoard.models import InstanceImgBoard

def imageSaver():
    pass

def backup(cycle):
    print("this function runs every", cycle, "seconds")
    import openstack_controller as oc                            # import는 여기 고정 -> 컴파일 시간에 circular import 때문에 걸려서
    openstack_hostIP = oc.hostIP

    try:
        instance_count = OpenstackInstance.objects.filter(backup_time=cycle).count()
        if instance_count == 0:
            return "백업 주기 ", cycle, "시간짜리 instance 없음"

        token = oc.admin_token()
        backup_instance_list = OpenstackInstance.objects.filter(backup_time=cycle)
        print(cycle, "시간짜리 리스트: ", backup_instance_list)

        for instance in backup_instance_list:
            print("인스턴스 오브젝트: ", instance)
            backup_instance_id = instance.instance_id
            print("인스턴스 id: ", backup_instance_id)
            backup_payload = {
                "createBackup": {
                    "name": "Backup " + backup_instance_id,
                    "backup_type": "daily",
                    "rotation": 1
                }
            }
            backup_req = requests.post("http://" + openstack_hostIP + "/compute/v2.1/servers/" +
                backup_instance_id + "/action",
                headers={"X-Auth-Token": token},    # admin토큰임 ㅋㅋ
                data=json.dumps(backup_payload))

            instance_image_URL = backup_req.headers["Location"]
            print("image_URL : " + instance_image_URL)
            instance_image_ID = instance_image_URL.split("/")[6]
            print("image_ID : " + instance_image_ID)

            while(True):
                image_status_req = requests.get("http://" + openstack_hostIP + "/image/v2/images/" + instance_image_ID,
                headers = {"X-Auth-Token" : token})
                print("이미지 상태 조회 리스폰스: ", image_status_req.json())
                image_status = image_status_req.json()["status"]
                if image_status == "active":
                    break
                time.sleep(2)

            image_download_req = requests.get("http://" + openstack_hostIP + "/image/v2/images/" + instance_image_ID + "/file",
                headers = {"X-Auth-Token" : token})
            file = open("C:/Users/YOUNGHOO KIM/Desktop/PNU/Graduation/codes/cloudmanager/back_imgs/" + backup_instance_id + ".qcow2", "wb")
            file.write(image_download_req.content)
            file.close()

            backup_image_data = {
                "instance_id" : backup_instance_id,
                "image_id" : instance_image_ID,
                "image_url" : instance_image_URL
            }

            print(backup_image_data)

            if OpenstackBackupImage.objects.filter(instance_id=backup_instance_id).count() == 0:   # 해당 이미지가 DB에 저장 안돼있으면 create()
                serializer = OpenstackBackupImageSerializer(data=backup_image_data)
                if serializer.is_valid():
                    serializer.save()
                    print("saved image info")
                    print(serializer.data)
                else:
                    print("not saved")
                    print(serializer.errors)

            else:   # 해당 이미지가 DB에 저장돼있으면 update()
                backup_img_to_update = OpenstackBackupImage.objects.filter(instance_id=backup_instance_id)
                backup_img_to_update.update(image_id=instance_image_ID)
                backup_img_to_update.update(image_url=instance_image_URL)
                print("updated")

            return "image file download response is ", backup_req

    except OperationalError:
            return "인스턴스가 없습니다."

def backup6():
    backup_res = backup(6)
    print(backup_res)


def backup12():
    backup_res = backup(12)
    print(backup_res)

def deleter():
    OpenstackBackupImage.objects.all().delete()
    print("all-deleted")

def start():
    scheduler = BackgroundScheduler()
    # scheduler.add_job(deleter, 'interval', seconds=5)
    scheduler.add_job(backup6, 'interval', seconds=30)
    scheduler.add_job(backup12, 'interval', seconds=60)
    
    scheduler.start()
