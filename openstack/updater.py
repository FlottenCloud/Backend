import os
import json
from re import S
import time
# import paramiko
from sqlite3 import OperationalError
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.files import File
from openstack.models import OpenstackBackupImage, OpenstackInstance
from openstack.serializers import OpenstackBackupImageSerializer
from openstack.openstack_modules import RequestChecker


def freezerBackup(cycle):
    print("this function runs every", cycle, "seconds")
    pass


# def imageSaver(backup_img_file):
#     if InstanceImgBoard.objects.filter(instance_img_file=backup_img_file).exists():
#         backup_img_to_update = InstanceImgBoard.objects.filter(instance_img_file=backup_img_file)
#         # backup_img.update(instance_img_file=backup_img_file)

#     document = InstanceImgBoard(
#         instance_img_file = backup_img_file
#     )
#     document.save()
#     documents = InstanceImgBoard.objects.all()
#     # print(list(documents))

#     return list(documents)


def backup(cycle):
    import openstack_controller as oc                            # import는 여기 고정 -> 컴파일 시간에 circular import 때문에 걸려서
    openstack_hostIP = oc.hostIP

    print("this function runs every", cycle, "seconds")
    req_checker = RequestChecker()

    try:
        instance_count = OpenstackInstance.objects.filter(backup_time=cycle).count()
        if instance_count == 0:
            return "백업 주기 ", cycle, "시간짜리 instance 없음"

        admin_token = oc.admin_token()
        if admin_token == None:
            return "오픈스택서버 고장"
        
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
            backup_req = req_checker.reqCheckerWithData("post", "http://" + openstack_hostIP + "/compute/v2.1/servers/" +
                backup_instance_id + "/action", admin_token,
                json.dumps(backup_payload))
            if backup_req == None:
                raise requests.exceptions.Timeout
            # backup_req = requests.post("http://" + openstack_hostIP + "/compute/v2.1/servers/" +
            #     backup_instance_id + "/action",
            #     headers={"X-Auth-Token": admin_token},    # admin토큰임 ㅋㅋ
            #     data=json.dumps(backup_payload))

            instance_image_URL = backup_req.headers["Location"]
            print("image_URL : " + instance_image_URL)
            instance_image_ID = instance_image_URL.split("/")[6]
            print("image_ID : " + instance_image_ID)

            while(True):
                image_status_req = req_checker.reqChecker("get", "http://" + openstack_hostIP + "/image/v2/images/" + instance_image_ID, admin_token)
                if image_status_req == None:
                    raise requests.exceptions.Timeout
                print("이미지 상태 조회 리스폰스: ", image_status_req.json())

                image_status = image_status_req.json()["status"]
                if image_status == "active":
                    break
                time.sleep(2)
            image_download_req = req_checker.reqChecker("get", "http://" + openstack_hostIP + "/image/v2/images/" + instance_image_ID + "/file", admin_token)
            if image_download_req == None:
                raise requests.exceptions.Timeout
            print("오픈스택에서의 이미지 다운로드에 대한 리스폰스: ", image_download_req)
            backup_img_file = open(backup_instance_id + ".qcow2", "wb")
            backup_img_file.write(image_download_req.content)
            backup_img_file.close()

            backup_img_file_to_db = open(backup_instance_id + ".qcow2", "rb")
            backup_image_data = {
                "instance_id" : backup_instance_id,
                "image_id" : instance_image_ID,
                "image_url" : instance_image_URL,
                "instance_img_file" : File(backup_img_file_to_db)
            }
            print(backup_image_data)

            if OpenstackBackupImage.objects.filter(instance_id=backup_instance_id).exists():
                OpenstackBackupImage.objects.filter(instance_id=backup_instance_id).delete()
                serializer = OpenstackBackupImageSerializer(data=backup_image_data)
                if serializer.is_valid():
                    serializer.save()
                    print("updated image info")
                    print(serializer.data)
                    backup_img_file_to_db.close()
                    os.remove(backup_instance_id + ".qcow2")
                else:
                    print("not updated")
                    print(serializer.errors)
                    backup_img_file_to_db.close()
                    os.remove(backup_instance_id + ".qcow2")

                    print("not updated")# return "not updated"
                    pass


                backup_img_file_to_db.close()
                print("updated")

            else:
                serializer = OpenstackBackupImageSerializer(data=backup_image_data)
                if serializer.is_valid():
                    serializer.save()
                    print("saved image info")
                    print(serializer.data)
                    backup_img_file_to_db.close()
                    os.remove(backup_instance_id + ".qcow2")
                else:
                    print("not saved")
                    print(serializer.errors)
                    backup_img_file_to_db.close()                    
                    os.remove(backup_instance_id + ".qcow2")

                    print("not saved")# return "not saved"
                    pass
            
            # return "image file download response is ", backup_req
            print("Backup for " + backup_instance_id + " is completed")
        return "All backup has completed."

    except OperationalError:
            return "인스턴스가 없습니다."
    except requests.exceptions.Timeout:
        return "오픈스택서버 고장"
    except requests.exceptions.ConnectionError:
            return "요청이 거부되었습니다."

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
    scheduler = BackgroundScheduler() # ({'apscheduler.job_defaults.max_instances': 2}) # max_instance = 한 번에 실행할 수 있는 같은 job의 개수
    # scheduler.add_job(deleter, 'interval', seconds=5)
    scheduler.add_job(backup6, 'interval', seconds=30)
    # scheduler.add_job(backup12, 'interval', seconds=120)
    
    scheduler.start()
