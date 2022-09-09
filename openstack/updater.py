import os
import json
from re import S
import time
import paramiko
from sqlite3 import OperationalError
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.files import File
from openstack.models import OpenstackBackupImage, OpenstackInstance
from openstack.serializers import OpenstackBackupImageSerializer
from openstack.openstack_modules import RequestChecker


# ------------------------------Freezer Backup------------------------------ #

def writeTxtFile(mode, instance_id):
    file = open("freezer_" + mode +"_template.txt", "w", encoding="UTF-8")
    file.write('source admin-openrc.sh')                         #환경에 맞게 설정해야됨 본인 리눅스 환경
    file.write('\nfreezer-agent --action ' + mode + ' --nova-inst-id ')
    file.write(instance_id)
    file.write(
        ' --storage local --container /home/hoo/' + instance_id + '_backup' + ' --backup-name ' + instance_id + '_backup' + ' --mode nova --engine nova --no-incremental true')
    file.close()

def readTxtFile(mode):               #mode : backup, restore
    file = open("freezer_" + mode +"_template.txt", "r", encoding="UTF-8")
    data = []
    while (1):
        line = file.readline()
        try:
            escape = line.index('\n')
        except:
            escape = len(line)

        if line:
            data.append(line[0:escape])
        else:
            break
    file.close()
    print(data)

    return data

def freezerBackup(instance_id):
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    server = "119.198.160.6"
    user = "hoo"                                      #리눅스 Host ID
    pwd = "0000"                                       #리눅스 Host Password
    cli.connect(server, port=10022, username=user, password=pwd)

    writeTxtFile("backup", instance_id)
    commandLines = readTxtFile("backup") # 메모장 파일에 적어놨던 명령어 텍스트 읽어옴
    print(commandLines)

    stdin, stdout, stderr = cli.exec_command(";".join(commandLines)) # 명령어 실행
    lines = stdout.readlines() # 실행한 명령어에 대한 결과 텍스트
    resultData = ''.join(lines)
    print(resultData) # 결과 확인
    cli.close()

def freezerRestore(instance_id):
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    server = "119.198.160.6"
    user = "hoo"
    pwd = "0000"
    cli.connect(server, port=10022, username=user, password=pwd)

    writeTxtFile("restore", instance_id)
    commandLines = readTxtFile("restore") # 메모장 파일에 적어놨던 명령어 텍스트 읽어옴
    print(commandLines)

    stdin, stdout, stderr = cli.exec_command(";".join(commandLines)) # 명령어 실행
    lines = stdout.readlines() # 실행한 명령어에 대한 결과 텍스트
    resultData = ''.join(lines)
    print(resultData) # 결과 확인
    cli.close()


# def freezerRestoreWithCycle(cycle):
#     # print("freezerRestore With Cycle function Start!!")
#     # error_instance_count = OpenstackInstance.objects.filter(status="ERROR").count()
#     # if error_instance_count == 0:
#     #     print("Error 상태의 instance 없음")
#     # restore_instance_list = OpenstackInstance.objects.filter(status="ERROR")


def freezerBackupWithCycle(cycle):
    print("freezerBackup With Cycle function Start!!")

    try:
        instance_count = OpenstackInstance.objects.filter(backup_time=cycle).count()
        if instance_count == 0:
            return "백업 주기 ", cycle, "시간짜리 instance 없음(freezer_backup_function)"

        backup_instance_list = OpenstackInstance.objects.filter(freezer_completed=True).filter(backup_time=cycle)
        print(cycle, "시간짜리 리스트(freezer_backup_function): ", backup_instance_list)
        if not backup_instance_list:
            print("리스트가 비어있음. 프리저 로컬 백업본 삭제 대상 없음.")
        else:
            for instance in backup_instance_list:
                print("인스턴스 오브젝트: ", instance)
                instance_id_for_OSremove = instance.instance_id
                print("인스턴스 id: ", instance_id_for_OSremove)

                #프리저 로컬 백업본 삭제 로직 시작
                try:
                    cli = paramiko.SSHClient()
                    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy)
                    server = "119.198.160.6"
                    user = "hoo"  # 리눅스 Host ID
                    pwd = "0000"  # 리눅스 Host Password
                    cli.connect(server, port=10022, username=user, password=pwd)
                    stdin, stdout, stderr = cli.exec_command("rm -rf " + instance_id_for_OSremove + "_backup")
                    print("리눅스 명령 수행 결과: ", ''.join(stdout.readlines()))
                    cli.close()
                except:
                    return "Error!! When removing freezer backup container!!"

                OpenstackInstance.objects.filter(instance_id=instance_id_for_OSremove).update(freezer_completed=False)

        backup_instance_list = OpenstackInstance.objects.filter(freezer_completed=False).filter(backup_time=cycle)
        for instance in backup_instance_list:
            print("인스턴스 오브젝트: ", instance)
            backup_instance_id = instance.instance_id
            print("인스턴스 id: ", backup_instance_id)

            try:
                freezerBackup(backup_instance_id)
            except:
                return ("Error!! When trying freezer Backup")

            OpenstackInstance.objects.filter(instance_id=backup_instance_id).update(freezer_completed=True)
        return "All freezerBackupWithCycle has completed"

    except OperationalError:
        return "인스턴스가 없습니다."

def freezerBackup6():
    freezer_backup_res = freezerBackupWithCycle(6)
    print(freezer_backup_res)


# ------------------------------Image Backup------------------------------ #

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
                    print("not updated")
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
    # scheduler.add_job(backup6, 'interval', seconds=30)
    # scheduler.add_job(backup12, 'interval', seconds=120)
    scheduler.add_job(freezerBackup6, 'interval', seconds=60)
    
    scheduler.start()
