import json
import time
from sqlite3 import OperationalError
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from openstack.models import OpenstackBackupImage, OpenstackInstance


def backup6():
    print("this function runs every 60 seconds")
    import openstack_controller as oc                            # import는 여기 고정
    openstack_hostIP = oc.hostIP

    try:
        instance_count = OpenstackInstance.objects.filter(backup_time=6).count()
        if instance_count == 0:
            return print("백업 주기 6시간짜리 instance 없음")

        token = oc.admin_token()
        backup_instance_list  = OpenstackInstance.objects.filter(backup_time=6)
        print("6시간짜리 리스트: ", backup_instance_list)

        for instance in backup_instance_list:
            print("인스턴스 오브젝트: ", instance)
            instance_id = instance.instance_id
            print("인스턴스 id: ", instance_id)
            backup_payload = {
                "createBackup": {
                    "name": "Backup " + instance_id,
                    "backup_type": "daily",
                    "rotation": 1
                }
            }
            backup_req = requests.post("http://" + openstack_hostIP + "/compute/v2.1/servers/" +
                instance_id + "/action",
                headers={"X-Auth-Token": token},    # admin토큰임 ㅋㅋ
                data=json.dumps(backup_payload))

            instance_image_URL = backup_req.headers["Location"]
            print("image_URL : " + instance_image_URL)
            instance_image_ID = instance_image_URL.split("/")[6]
            print("image_ID : " + instance_image_ID)

            OpenstackBackupImage.objects.create(
                instance_id = instance_id,
                image_id = instance_image_ID,
                image_url = instance_image_URL
            )

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
            file = open("C:/Users/YOUNGHOO KIM/Desktop/PNU/Graduation/codes/cloudmanager/back_imgs/" + instance_id + ".qcow2", "wb")
            file.write(image_download_req.content)
            file.close()

            print("image file download response is", backup_req)
    
    except OperationalError:
        return print("인스턴스가 없습니다.")


def backup12():
    print("this function runs every 60 seconds")
    import openstack_controller as oc                            # import는 여기 고정
    openstack_hostIP = oc.hostIP

    try:
        instance_count = OpenstackInstance.objects.filter(backup_time=12).count()
        if instance_count == 0:
            return print("백업 주기 12시간짜리 instance 없음")

        token = oc.admin_token()
        backup_instance_list = OpenstackInstance.objects.filter(backup_time=12)
        print("6시간짜리 리스트: ", backup_instance_list)

        for instance in backup_instance_list:
            print("인스턴스 오브젝트: ", instance)
            instance_id = instance.instance_id
            print("인스턴스 id: ", instance_id)
            backup_payload = {
                "createBackup": {
                    "name": "Backup " + instance_id,
                    "backup_type": "daily",
                    "rotation": 1
                }
            }
            backup_req = requests.post("http://" + openstack_hostIP + "/compute/v2.1/servers/" +
                instance_id + "/action",
                headers={"X-Auth-Token": token},    # admin토큰임 ㅋㅋ
                data=json.dumps(backup_payload))

            instance_image_ID = backup_req.headers["Location"]
            print("image_URL : " + instance_image_ID)
            instance_image_URL = instance_image_ID.split("/")[6]
            print("image_ID : " + instance_image_URL)

            OpenstackBackupImage.objects.create(
                instance_id = instance_id,
                image_id = instance_image_ID,
                image_url = instance_image_URL
            )

            while(True):
                image_status_req = requests.get("http://" + openstack_hostIP + "/image/v2/images/" + instance_image_URL,
                headers = {"X-Auth-Token" : token})
                print("이미지 상태 조회 리스폰스: ", image_status_req.json())
                image_status = image_status_req.json()["status"]
                if image_status == "active":
                    break
                time.sleep(2)

            image_download_req = requests.get("http://" + openstack_hostIP + "/image/v2/images/" + instance_image_URL + "/file",
                headers = {"X-Auth-Token" : token})
            file = open("C:/Users/YOUNGHOO KIM/Desktop/PNU/Graduation/codes/cloudmanager/back_imgs/" + instance_id + ".qcow2", "wb")
            file.write(image_download_req.content)
            file.close()

            print("image file download response is", backup_req)

    except OperationalError:
            return print("인스턴스가 없습니다.")

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(backup6, 'interval', seconds=30)
    scheduler.add_job(backup12, 'interval', seconds=60)
    
    scheduler.start()
