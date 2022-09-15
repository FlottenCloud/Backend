from email.contentmanager import raw_data_manager
from ipaddress import ip_address
import os
import json
from pipes import Template
from re import S
import time
from urllib.request import Request
import paramiko
from sqlite3 import OperationalError
import requests
import webbrowser
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.files import File
from django.http import JsonResponse
from account.models import AccountInfo

from openstack.models import OpenstackBackupImage, OpenstackInstance
from cloudstack.models import CloudstackInstance
from openstack.serializers import OpenstackInstanceSerializer,OpenstackBackupImageSerializer
from openstack.openstack_modules import RequestChecker, Stack, TemplateModifier


# ------------------------------Freezer Backup------------------------------ #

# def writeTxtFile(mode, instance_id):
#     file = open("freezer_" + mode +"_template.txt", "w", encoding="UTF-8")
#     file.write('source admin-openrc.sh')                         #환경에 맞게 설정해야됨 본인 리눅스 환경
#     file.write('\nfreezer-agent --action ' + mode + ' --nova-inst-id ')
#     file.write(instance_id)
#     file.write(
#         ' --storage local --container /home/hoo/' + instance_id + '_backup' + ' --backup-name ' + instance_id + '_backup' + ' --mode nova --engine nova --no-incremental true')
#     file.close()

# def readTxtFile(mode):               #mode : backup, restore
#     file = open("freezer_" + mode +"_template.txt", "r", encoding="UTF-8")
#     data = []
#     while (1):
#         line = file.readline()
#         try:
#             escape = line.index('\n')
#         except:
#             escape = len(line)

#         if line:
#             data.append(line[0:escape])
#         else:
#             break
#     file.close()
#     print(data)

#     return data

# def freezerBackup(instance_id):
#     cli = paramiko.SSHClient()
#     cli.set_missing_host_key_policy(paramiko.AutoAddPolicy)
#     server = "119.198.160.6"
#     user = "hoo"                                      #리눅스 Host ID
#     pwd = "0000"                                       #리눅스 Host Password
#     cli.connect(server, port=10022, username=user, password=pwd)

#     writeTxtFile("backup", instance_id)
#     commandLines = readTxtFile("backup") # 메모장 파일에 적어놨던 명령어 텍스트 읽어옴
#     print(commandLines)

#     stdin, stdout, stderr = cli.exec_command(";".join(commandLines)) # 명령어 실행
#     lines = stdout.readlines() # 실행한 명령어에 대한 결과 텍스트
#     resultData = ''.join(lines)
#     print(resultData) # 결과 확인
#     cli.close()

# def freezerRestore(instance_id):
#     cli = paramiko.SSHClient()
#     cli.set_missing_host_key_policy(paramiko.AutoAddPolicy)
#     server = "119.198.160.6"
#     user = "hoo"
#     pwd = "0000"
#     cli.connect(server, port=10022, username=user, password=pwd)

#     writeTxtFile("restore", instance_id)
#     commandLines = readTxtFile("restore") # 메모장 파일에 적어놨던 명령어 텍스트 읽어옴
#     print(commandLines)

#     stdin, stdout, stderr = cli.exec_command(";".join(commandLines)) # 명령어 실행
#     lines = stdout.readlines() # 실행한 명령어에 대한 결과 텍스트
#     resultData = ''.join(lines)
#     print(resultData) # 결과 확인
#     cli.close()


# # def freezerRestoreWithCycle(cycle):
# #     # print("freezerRestore With Cycle function Start!!")
# #     # error_instance_count = OpenstackInstance.objects.filter(status="ERROR").count()
# #     # if error_instance_count == 0:
# #     #     print("Error 상태의 instance 없음")
# #     # restore_instance_list = OpenstackInstance.objects.filter(status="ERROR")


# def freezerBackupWithCycle(cycle):
#     print("freezerBackup With Cycle function Start!!")

#     try:
#         instance_count = OpenstackInstance.objects.filter(backup_time=cycle).count()
#         if instance_count == 0:
#             return "백업 주기 ", cycle, "시간짜리 instance 없음(freezer_backup_function)"

#         backup_instance_list = OpenstackInstance.objects.filter(freezer_completed=True).filter(backup_time=cycle)
#         print(cycle, "시간짜리 리스트(freezer_backup_function): ", backup_instance_list)
#         if not backup_instance_list:
#             print("리스트가 비어있음. 프리저 로컬 백업본 삭제 대상 없음.")
#         else:
#             for instance in backup_instance_list:
#                 print("인스턴스 오브젝트: ", instance)
#                 instance_id_for_OSremove = instance.instance_id
#                 print("인스턴스 id: ", instance_id_for_OSremove)

#                 #프리저 로컬 백업본 삭제 로직 시작
#                 try:
#                     cli = paramiko.SSHClient()
#                     cli.set_missing_host_key_policy(paramiko.AutoAddPolicy)
#                     server = "119.198.160.6"
#                     user = "hoo"  # 리눅스 Host ID
#                     pwd = "0000"  # 리눅스 Host Password
#                     cli.connect(server, port=10022, username=user, password=pwd)
#                     stdin, stdout, stderr = cli.exec_command("rm -rf " + instance_id_for_OSremove + "_backup")
#                     print("리눅스 명령 수행 결과: ", ''.join(stdout.readlines()))
#                     cli.close()
#                 except:
#                     return "Error!! When removing freezer backup container!!"

#                 OpenstackInstance.objects.filter(instance_id=instance_id_for_OSremove).update(freezer_completed=False)

#         backup_instance_list = OpenstackInstance.objects.filter(freezer_completed=False).filter(backup_time=cycle)
#         for instance in backup_instance_list:
#             print("인스턴스 오브젝트: ", instance)
#             backup_instance_id = instance.instance_id
#             print("인스턴스 id: ", backup_instance_id)

#             try:
#                 freezerBackup(backup_instance_id)
#             except:
#                 return ("Error!! When trying freezer Backup")

#             OpenstackInstance.objects.filter(instance_id=backup_instance_id).update(freezer_completed=True)
#         return "All freezerBackupWithCycle has completed"

#     except OperationalError:
#         return "인스턴스가 없습니다."

# def freezerBackup6():
#     freezer_backup_res = freezerBackupWithCycle(6)
#     print(freezer_backup_res)


# ------------------------------Backup Part------------------------------ #

def getTemplatestatus(admin_apiKey, admin_secretKey, template_name):
    import cloudstack_controller as csc
    
    request_body = {"apiKey" : admin_apiKey, "response" : "json", "command" : "listTemplates", "templatefilter" : "selfexecutable", "name" : template_name}
    template_status_get_req = csc.requestThroughSig(admin_secretKey, request_body)
    template_status_get_res = json.loads(template_status_get_req) #template_status_get_req.json()
    # print("템플릿 다운로드 상태(in json): ", template_status_get_res)
    if len(template_status_get_res["listtemplatesresponse"]) != 2: #0 or len(template_status_get_res["listtemplatesresponse"]) == 1:
        template_download_status = "Download Not Completed"
    else:
        template_download_status = template_status_get_res["listtemplatesresponse"]["template"][0]["status"]
        
    print("Template status is ", template_download_status)
    
    return template_download_status

def templateIDgetter(admin_apiKey, admin_secretKey, template_name):
    import cloudstack_controller as csc
    
    request_body = {"apiKey" : admin_apiKey, "response" : "json", "command" : "listTemplates", "templatefilter" : "selfexecutable", "name" : template_name}
    template_id_get_req = csc.requestThroughSig(admin_secretKey, request_body)
    template_id_get_res = json.loads(template_id_get_req)
    templateID = template_id_get_res["listtemplatesresponse"]["template"][0]["id"]
    print("Template id is ", templateID)
    
    return templateID

def registerCloudstackTemplate(zoneID, template_name, backup_img_file_name, os_type_id):
    import cloudstack_controller as csc
    admin_apiKey = csc.admin_apiKey
    admin_secretKey = csc.admin_secretKey

    request_body = {"apiKey" : admin_apiKey, "response" : "json", "command" : "registerTemplate",
        "displaytext" : template_name, "format" : "qcow2", "hypervisor" : "kvm",
        "name" : template_name, "url" : "http://119.198.160.6:8000/media/img-files/" + backup_img_file_name, "ostypeid" : os_type_id, "zoneid" : zoneID}
    template_register_req = csc.requestThroughSigForTemplateRegist(admin_secretKey, request_body)
    webbrowser.open(template_register_req)  # url 오픈으로 해결 안돼서 webbrowser로 open함
    
    while True :
        template_status = getTemplatestatus(admin_apiKey, admin_secretKey, template_name)
        if template_status == "Download Complete":
            break
        else :
            if template_status == "error" :
                print("이미지 등록이 정상적으로 실행되지 않았습니다.")
                break
            else:
                print("wait until image status active. Current status is ", template_status)
            time.sleep(5)

    backup_template_id = templateIDgetter(admin_apiKey, admin_secretKey, template_name)
    print("Registered template " + backup_img_file_name + " to cloudstack")
    
    return backup_template_id

def deployCloudstackInstance(user_id, user_apiKey, user_secretKey, instance_name, cloudstack_user_network_id, backup_img_file_name, os_type):
    import cloudstack_controller as csc
    zoneID = csc.zoneID
    domainID = csc.domainID
    hostID = csc.hostID
    small_offeringID = csc.small_offeringID
    medium_offeringID = csc.medium_offeringID
    
    user_id_instance = AccountInfo.objects.get(user_id=user_id)
    template_name = instance_name + "Template"
    if os_type == "ubuntu" :     # ubuntu(18.04 LTS)
        os_type_id = "b3ce66f1-34ed-11ed-914c-0800270aea06"  #"12bc219b-fdcb-11ec-a9c1-08002765d220"
    elif os_type == "centos" :   # centos
        os_type_id = "abc"
    else:   # fedora(openstack default)
        os_type_id = "26e61d3e-246f-4822-8a66-6a8b08806d7e"   #"8682cef8-a3f3-47a0-886d-87b9398469b3"
    
    backup_template_id = registerCloudstackTemplate(zoneID, template_name, backup_img_file_name, os_type_id)
    
    instance_deploy_req_body = {"apiKey" : user_apiKey, "response" : "json", "command" : "deployVirtualMachine",
        "networkids" : cloudstack_user_network_id, "serviceofferingId" : medium_offeringID,
        'templateId': backup_template_id, "zoneId": zoneID,
        "displayname" : instance_name, "name" : instance_name, "domainid" : domainID,
        "account" : user_id, "hostid" : hostID, "startvm" : "false"
    }
    try :
        print("인스턴스 생성 시작")
        instance_deploy_req = csc.requestThroughSig(user_secretKey, instance_deploy_req_body)
    except Exception as e:
        print("에러 내용: ", e)
    
    while(True):    
        instance_info_req_body = {"apiKey" : user_apiKey, "response" : "json", "command" : "listVirtualMachines", "name" : instance_name}
        instance_info_req = csc.requestThroughSig(user_secretKey, instance_info_req_body)
        instance_info_res = json.loads(instance_info_req)
        
        if len(instance_info_res["listvirtualmachinesresponse"]) != 0:
            created_instance_id = instance_info_res["listvirtualmachinesresponse"]["virtualmachine"][0]["id"]
            created_instance_name = instance_info_res["listvirtualmachinesresponse"]["virtualmachine"][0]["name"]
            created_instance_status = instance_info_res["listvirtualmachinesresponse"]["virtualmachine"][0]["state"]
            created_instance_ip_address = "10.0.0.1"
            created_instance_image_id = instance_info_res["listvirtualmachinesresponse"]["virtualmachine"][0]["templateid"]
            created_instance_flavor_name = "MEDIUM"
            created_instance_ram_size = round(instance_info_res["listvirtualmachinesresponse"]["virtualmachine"][0]["memory"]/1024, 2)
            created_instance_disk_size = 5
            created_instance_num_cpu = instance_info_res["listvirtualmachinesresponse"]["virtualmachine"][0]["cpunumber"]
            break
        
        time.sleep(1)
    
    # db에 user_id, instance_id, image_id(template_id), ip_address, instance_name, status, flavor_name(medium 고정일 듯), ram_size(1G고정일 듯), disk_size, num_cpu 저장
    CloudstackInstance.objects.create(
        user_id = user_id_instance,
        instance_id = created_instance_id,
        instance_name = created_instance_name,
        ip_address = created_instance_ip_address,
        status = created_instance_status,
        image_id = created_instance_image_id,
        flavor_name = created_instance_flavor_name,
        ram_size = created_instance_ram_size,
        disk_size = created_instance_disk_size,
        num_cpu = created_instance_num_cpu
    )

    print("Created Instance " + backup_img_file_name + " to cloudstack")

    return backup_template_id, instance_deploy_req

def deleteCloudstackInstanceAndTemplate(admin_apiKey, admin_secretKey, instance_id, template_id):
    import cloudstack_controller as csc

    instance_del_req_body = {"apiKey": admin_apiKey, "response": "json", "command": "expungeVirtualMachine",
                   "id": instance_id, "expunge": "true"}
    instance_del_req = csc.requestThroughSig(admin_secretKey, instance_del_req_body)
    
    time.sleep(2)
    
    template_del_req_body = {"apiKey": admin_apiKey, "response": "json", "command": "deleteTemplate",
                "id": template_id}

    template_del_req = csc.requestThroughSig(admin_secretKey, template_del_req_body)
    
    return instance_del_req, template_del_req


def CloudstackInstanceDeleteAndCreate(user_id, cloudstack_user_apiKey, cloudstack_user_secretKey, backup_instance_name, cloudstack_user_network_id, backup_img_file_name, backup_instance_os_type):
    import cloudstack_controller as csc
    admin_apiKey = csc.admin_apiKey
    admin_secretKey = csc.admin_secretKey

    del_cloudstack_instance_info = CloudstackInstance.objects.get(backup_instance_name + "Template")
    del_instance_id = del_cloudstack_instance_info.instance_id
    del_template_id = del_cloudstack_instance_info.template_id
    
    instance_del_req, template_del_req = deleteCloudstackInstanceAndTemplate(admin_apiKey, admin_secretKey, del_instance_id, del_template_id)

    # ---삭제하고 타이밍 얼마나 줄 지 생각해볼 것--- #

    backup_template_id, instance_deploy_req = deployCloudstackInstance(user_id, cloudstack_user_apiKey, cloudstack_user_secretKey, backup_instance_name, cloudstack_user_network_id, backup_img_file_name, backup_instance_os_type)

    return backup_template_id, instance_deploy_req

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
            backup_instance_name = instance.instance_name
            backup_instance_os_type = instance.os
            user_id = instance.user_id.user_id
            cloudstack_user_network_id = instance.user_id.cloudstack_network_id
            cloudstack_user_apiKey = instance.user_id.cloudstack_apiKey
            cloudstack_user_secretKey = instance.user_id.cloudstack_secretKey
            print("클라우드 스택의 유저 네트워크 id: ", cloudstack_user_network_id)
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
            print("이미지 생성 request status code: ", backup_req.status_code)
            if backup_req == None:
                raise requests.exceptions.Timeout
            elif backup_req.status_code == 409:
                return "이미지 생성 불가"

            instance_image_URL = backup_req.headers["Location"]
            print("image_URL : " + instance_image_URL)
            instance_image_ID = instance_image_URL.split("/")[6]
            print("image_ID : " + instance_image_ID)

            while(True):
                image_status_req = req_checker.reqChecker("get", "http://" + openstack_hostIP + "/image/v2/images/" + instance_image_ID, admin_token)
                if image_status_req == None:
                    raise requests.exceptions.Timeout
                print("이미지 상태 조회 status: ", image_status_req)
                print("이미지 상태 조회 리스폰스: ", image_status_req.json())

                image_status = image_status_req.json()["status"]
                if image_status == "active":
                    break
                time.sleep(5)
            image_download_req = req_checker.reqChecker("get", "http://" + openstack_hostIP + "/image/v2/images/" + instance_image_ID + "/file", admin_token)
            if image_download_req == None:
                raise requests.exceptions.Timeout
            print("오픈스택에서의 이미지 다운로드에 대한 리스폰스: ", image_download_req)
            backup_img_file = open(backup_instance_id + ".qcow2", "wb")
            backup_img_file.write(image_download_req.content)
            backup_img_file.close()

            backup_img_file_name = backup_instance_id + ".qcow2"
            backup_img_file_to_db = open(backup_instance_id + ".qcow2", "rb")
            backup_image_data = {
                "instance_id" : backup_instance_id,
                "image_id" : instance_image_ID,
                "image_url" : instance_image_URL,
                "instance_img_file" : File(backup_img_file_to_db)
            }
            print(backup_image_data)

            if OpenstackBackupImage.objects.filter(instance_id=backup_instance_id).exists():    # 한 번 백업을 해놨을 경우
                OpenstackBackupImage.objects.filter(instance_id=backup_instance_id).delete()
                serializer = OpenstackBackupImageSerializer(data=backup_image_data)
                if serializer.is_valid():
                    serializer.save()
                    print("Updated backup data info")
                    print(serializer.data)
                    backup_img_file_to_db.close()
                    os.remove(backup_instance_id + ".qcow2")

                    #------cloudstack instance expunge, template delete & template register, instance deploy------#
                    backup_template_id, instance_deploy_req = deployCloudstackInstance(user_id, cloudstack_user_apiKey, cloudstack_user_secretKey, backup_instance_name, cloudstack_user_network_id, backup_img_file_name, backup_instance_os_type)
                    # backup_template_id, instance_deploy_req = CloudstackInstanceDeleteAndCreate(user_id, cloudstack_user_apiKey, cloudstack_user_secretKey, backup_instance_name, cloudstack_user_network_id, backup_img_file_name, backup_instance_os_type)
                    
                else:
                    print("Backup data not updated")
                    print(serializer.errors)
                    backup_img_file_to_db.close()
                    os.remove(backup_instance_id + ".qcow2")
                    print("Backup data not updated")
                    pass

                backup_img_file_to_db.close()
                print("updated")

            else:   # 백업을 해놓지 않은 경우
                serializer = OpenstackBackupImageSerializer(data=backup_image_data)
                if serializer.is_valid():
                    serializer.save()
                    print("Saved Backup data info")
                    print(serializer.data)
                    backup_img_file_to_db.close()
                    os.remove(backup_instance_id + ".qcow2")
                    
                    #------cloudstack template register & instance deploy------#
                    backup_template_id, instance_deploy_req = deployCloudstackInstance(user_id, cloudstack_user_apiKey, cloudstack_user_secretKey, backup_instance_name, cloudstack_user_network_id, backup_img_file_name, backup_instance_os_type)
                    
                else:
                    print("Backup data not saved")
                    print(serializer.errors)
                    backup_img_file_to_db.close()                    
                    os.remove(backup_instance_id + ".qcow2")
                    print("Backup data not saved")
                    pass
        
            print("Backup for " + backup_instance_id + " is completed")    
        
        return "All backup has completed."

    except OperationalError:
            return "인스턴스가 없습니다."
    except requests.exceptions.Timeout:
        return "오픈스택서버 고장"
    except requests.exceptions.ConnectionError:
            return "요청이 거부되었습니다."

# ------------------------------Restore Part------------------------------ #

def deleteStackbeforeRestore(user_id, user_token, tenant_id_for_restore, stack_id_for_del, stack_name_for_del, instance_update_image_id_for_del):
    import openstack_controller as oc
    token = oc.admin_token()
    openstack_hostIP = oc.hostIP
    req_checker = RequestChecker()
    
    print("삭제한 스택 이름: " + stack_name_for_del + "\n삭제한 스택 ID: " + stack_id_for_del)

    tenant_id_for_restore
    stack_del_req = req_checker.reqChecker("delete", "http://" + openstack_hostIP + "/heat-api/v1/" + tenant_id_for_restore + "/stacks/"
        + stack_name_for_del + "/" + stack_id_for_del, token)
    if stack_del_req == None:
        return "오픈스택 서버에 문제가 생겨 인스턴스(스택)을 삭제할 수 없습니다."
    
    if instance_update_image_id_for_del != None: # 업데이트를 한 번이라도 했을 시 업데이트에 쓰인 이미지도 삭제
        update_image_del_req = req_checker.reqChecker("delete", "http://" + openstack_hostIP + "/image/v2/images/" + instance_update_image_id_for_del, token)
        print("업데이트에 쓰인 이미지 삭제 리스폰스: ", update_image_del_req)
        if update_image_del_req == None:
            return "오픈스택 서버에 문제가 생겨 업데이트 때 사용한 이미지를 삭제할 수 없습니다."
    
    while(True):
        del_stack_status_req = req_checker.reqChecker("get", "http://" + openstack_hostIP + "/heat-api/v1/" + tenant_id_for_restore + "/stacks/" + stack_name_for_del + "/" + stack_id_for_del, token)
        if del_stack_status_req.json()["stack"]["stack_status"] == "DELETE_COMPLETE":
            print("스택 " + stack_name_for_del + " 삭제 완료")
            break
        
        print("스택 삭제 중")
        time.sleep(2)
    
    try:
        keypair_delete_req = req_checker.reqChecker("delete", "http://" + openstack_hostIP + "/compute/v2.1/os-keypairs/" + user_id + "_" + stack_name_for_del, user_token)
        print("키페어 삭제 완료")
    except Exception as e:
        print("키페어 삭제 요청의 에러 내용: ", e, " 요청에 대한 리스폰스 상태 코드: ", keypair_delete_req.status_code)
        pass
        
    OpenstackInstance.objects.get(stack_id=stack_id_for_del).delete()
    
    return "에러 발생한 스택 삭제 완료"

def errorCheckRestoreInOpenstack():
    import openstack_controller as oc
    admin_token = oc.admin_token()
    openstack_hostIP = oc.hostIP
    req_checker = RequestChecker()
    template_modifier = TemplateModifier()
    stack_saver = Stack()

    error_instance_list_req = req_checker.reqChecker("get", "http://" + openstack_hostIP + "/compute/v2.1/servers?status=ERROR&all_tenants=1", admin_token)
    print(error_instance_list_req)
    print(error_instance_list_req.json())
    error_instance_list = error_instance_list_req.json()["servers"]
    print("에러 상태인 인스턴스 리스트: ", error_instance_list)
    if len(error_instance_list) == 0:
        return print("에러상태인 인스턴스가 없습니다.")
    
    for error_instance in error_instance_list:
        OpenstackInstance.objects.filter(instance_id=error_instance["id"]).update(status="ERROR")
        print("instance " + error_instance["id"] + "에러 감지")
    
    restore_instance_list = OpenstackInstance.objects.filter(status="ERROR")
    for error_instance in restore_instance_list:
        user_id = error_instance.user_id.user_id
        user_password = error_instance.user_id.password
        instance_id_for_restore = error_instance.instance_id  # restore 할 인스턴스
        instance_name_for_restore = error_instance.instance_name
        stack_id_for_del = error_instance.stack_id
        stack_name_for_del = error_instance.stack_name
        instance_flavor_for_restore = error_instance.flavor_name
        instance_update_image_id_for_del = error_instance.update_image_ID
        instance_os_for_restore = error_instance.os
        instance_backup_time_for_restore = error_instance.backup_time
        print("복구할 인스턴스의 정보: ", instance_id_for_restore, instance_name_for_restore, instance_flavor_for_restore, instance_os_for_restore)
        tenant_id_for_restore = error_instance.user_id.openstack_user_project_id  # 유저 project id
        image_id_for_restore = error_instance.instance_backup_img_file.get(instance_id=instance_id_for_restore).image_id   # 유저 백업 img id
        image_name_for_restore = "Backup " + instance_id_for_restore
        print("복구에 쓰일 리소스 정보: ", tenant_id_for_restore, image_id_for_restore, image_name_for_restore)
        
        user_token = oc.user_token({"user_id" : user_id, "password" : user_password})
        delete_stack_res = deleteStackbeforeRestore(user_id, user_token, tenant_id_for_restore, stack_id_for_del, stack_name_for_del, instance_update_image_id_for_del)
        print(delete_stack_res)
        
        time.sleep(5)
        #-------스택 복구 시작-------#
        if instance_os_for_restore == "ubuntu":
            with open("templates/ubuntu_1804.json", "r") as f:   # 아직 템플릿 구현 안됨
                    json_template_skeleton = json.load(f)
                    json_template = template_modifier.templateModifyWhenRestore(image_name_for_restore, json_template_skeleton, user_id, instance_name_for_restore, instance_flavor_for_restore)
        elif instance_os_for_restore == "centos":
            with open("templates/cirros.json", "r") as f:    #일단 이거랑
                    json_template_skeleton = json.load(f)
                    json_template = template_modifier.templateModifyWhenRestore(image_name_for_restore, json_template_skeleton, user_id, instance_name_for_restore, instance_flavor_for_restore)
        elif instance_os_for_restore == "fedora":
            with open("templates/fedora.json", "r") as f:    #이걸로 생성 test
                    json_template_skeleton = json.load(f)
                    json_template = template_modifier.templateModifyWhenRestore(image_name_for_restore, json_template_skeleton, user_id, instance_name_for_restore, instance_flavor_for_restore)
        
        stack_req = req_checker.reqCheckerWithData("post", "http://" + openstack_hostIP + "/heat-api/v1/" + tenant_id_for_restore + "/stacks", user_token, json_template)
        if stack_req == None:
            return "오픈스택 서버에 문제가 생겨 스택 정보를 가져올 수 없습니다."
        print("stack생성", stack_req.json())
        stack_id = stack_req.json()["stack"]["id"]

        stack_name_req = req_checker.reqChecker("get", "http://" + openstack_hostIP + "/heat-api/v1/" + tenant_id_for_restore + "/stacks?id=" + stack_id, user_token)
        if stack_name_req == None:
            return "오픈스택 서버에 문제가 생겨 스택 이름을 가져올 수 없습니다."
        print("스택 이름 정보: ", stack_name_req.json())
        stack_name = stack_name_req.json()["stacks"][0]["stack_name"]

        try:
            instance_id, instance_name, instance_ip_address, instance_status, instance_image_name, instance_flavor_name, instance_ram_size, instance_disk_size, instance_num_cpu = stack_saver.stackResourceGetter("create", openstack_hostIP, tenant_id_for_restore, user_id, stack_name, stack_id, user_token)
        except Exception as e:  # stackResourceGetter에서 None이 반환 된 경우
            print("스택 정보 가져오는 중 에러 발생: ", e)
            return "오픈스택 서버에 문제가 생겨 생성된 스택의 정보를 불러올 수 없습니다."

        # db에 저장 할 인스턴스 정보
        instance_data = {
            "user_id" : user_id,
            "stack_id" : stack_id,
            "stack_name" : stack_name,
            "instance_id" : instance_id,
            "instance_name" : instance_name,
            "ip_address" : str(instance_ip_address),
            "status" : instance_status,
            "image_name" : instance_image_name,
            "flavor_name" : instance_flavor_name,
            "ram_size" : instance_ram_size,
            "disk_size" : instance_disk_size,
            "num_cpu" : instance_num_cpu,
            "backup_time" : instance_backup_time_for_restore,
            "os" : instance_os_for_restore
        }

        #serializing을 통한 인스턴스 정보 db 저장
        serializer = OpenstackInstanceSerializer(data=instance_data)
    
        if serializer.is_valid():
            serializer.save()
            print("saved")
            print(serializer.data)
        else:
            print("not saved")
            print(serializer.errors)
        
    return "복구 완료"


def backup6():
    backup_res = backup(6)
    print(backup_res)

def backup12():
    backup_res = backup(12)
    print(backup_res)
    
    

def deleter():
    AccountInfo.objects.all().delete()
    OpenstackInstance.objects.all().delete()
    OpenstackBackupImage.objects.all().delete()
    CloudstackInstance.objects.all().delete()
    print("all-deleted")


def start():
    scheduler = BackgroundScheduler() # ({'apscheduler.job_defaults.max_instances': 2}) # max_instance = 한 번에 실행할 수 있는 같은 job의 개수
    # scheduler.add_job(deleter, 'interval', seconds=2)
    # scheduler.add_job(backup6, 'interval', seconds=30)
    # scheduler.add_job(backup12, 'interval', seconds=120)
    # scheduler.add_job(freezerBackup6, 'interval', seconds=60)
    # scheduler.add_job(backup6, 'interval', seconds=20)
    # scheduler.add_job(errorCheckRestoreInOpenstack, 'interval', seconds=10)

    scheduler.start()
