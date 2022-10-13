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
from log_manager import InstanceLogManager, ServerLogManager
from account.models import AccountInfo
from openstack.models import OpenstackBackupImage, OpenstackInstance, ServerStatusFlag, ServerLog, DjangoServerTime
from cloudstack.models import CloudstackInstance
from openstack.serializers import OpenstackInstanceSerializer,OpenstackBackupImageSerializer
from openstack.openstack_modules import RequestChecker, Stack, TemplateModifier, Instance

ssh_ip_addr = ""
ssh_user_name = ""  # 리눅스 Host ID
ssh_password = ""  # 리눅스 Host Password
ssh_port = 22


# ------------------------------------------------------------ Instance Error Check Part ------------------------------------------------------------ #

def errorCheckAndUpdateDBstatus():
    import openstack_controller as oc
    admin_token = oc.admin_token()
    if admin_token == None:
        return print("오픈스택 서버가 고장나 에러상태인 인스턴스 리스트를 받아올 수 없습니다.")
    openstack_hostIP = oc.hostIP
    req_checker = RequestChecker()
    log_manager = InstanceLogManager()

    error_instance_list_req = req_checker.reqChecker("get", "http://" + openstack_hostIP + "/compute/v2.1/servers?status=ERROR&all_tenants=1", admin_token)
    print(error_instance_list_req)
    try:
        print(error_instance_list_req.json())
    except Exception as e:
        print("No instance in ERROR status")
        pass
    error_instance_list = error_instance_list_req.json()["servers"]
    print("에러 상태인 인스턴스 리스트: ", error_instance_list)
    if len(error_instance_list) == 0:
        return print("에러상태인 인스턴스가 없습니다.")
    
    for error_instance in error_instance_list:
        error_instance_id = error_instance["id"]
        error_openstack_instance = OpenstackInstance.objects.get(instance_id=error_instance_id)
        user_id = error_openstack_instance.user_id.user_id
        error_instance_pk = error_openstack_instance.instance_pk
        error_instance_name = error_openstack_instance.instance_name
        OpenstackInstance.objects.filter(instance_id=error_instance_id).update(status="ERROR")
        print("instance " + error_instance_id + "에러 감지")
        log_manager.userLogAdder(user_id, error_instance_name, "Error occurred", "instance")
        log_manager.instanceLogAdder(error_instance_pk, error_instance_name, "error_occurred", "Error occurred")


# ------------------------------------------------------------ Backup Part ------------------------------------------------------------ #

    # ------------------------------ Cloudstack Module ------------------------------ #
def templateStatusGetter(admin_apiKey, admin_secretKey, template_name):
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

def registerCloudstackTemplate(zoneID, template_name, backup_img_file_name, os_type_id):    # 템플릿 등록 코드
    import cloudstack_controller as csc
    admin_apiKey = csc.admin_apiKey
    admin_secretKey = csc.admin_secretKey

    request_body = {"apiKey" : admin_apiKey, "response" : "json", "command" : "registerTemplate",
        "displaytext" : template_name, "format" : "qcow2", "hypervisor" : "kvm",
        "name" : template_name, "url" : "https://hoograduation.s3.ap-northeast-2.amazonaws.com/img-files/" + backup_img_file_name, "ostypeid" : os_type_id, "zoneid" : zoneID}
    template_register_req = csc.requestThroughSigForTemplateRegister(admin_secretKey, request_body)
    webbrowser.open(template_register_req)  # url 오픈으로 해결 안돼서 webbrowser로 open함
    
    while True :    # 템플릿 등록이 다 됐는지 체크
        template_status = templateStatusGetter(admin_apiKey, admin_secretKey, template_name)
        if template_status == "Download Complete":  # 등록이 다 됐을 경우
            break
        else :  # 등록이 다 안된 경우
            if template_status == "error" :
                print("이미지 등록이 정상적으로 실행되지 않았습니다.")
                break
            else:
                print("wait until image status active. Current status is ", template_status)
            time.sleep(5)

    backup_template_id = templateIDgetter(admin_apiKey, admin_secretKey, template_name)
    print("Registered template " + backup_img_file_name + " to cloudstack")
    
    return backup_template_id

def deployCloudstackInstance(user_id, user_apiKey, user_secretKey, instance_pk, instance_name, cloudstack_user_network_id, backup_img_file_name, os_type):
    import cloudstack_controller as csc
    zoneID = csc.zoneID
    domainID = csc.domainID
    hostID = csc.hostID
    small_offeringID = csc.small_offeringID
    medium_offeringID = csc.medium_offeringID
    log_manager = InstanceLogManager()
    
    user_id_object = AccountInfo.objects.get(user_id=user_id)
    template_name = instance_name + "Template"
    if os_type == "ubuntu" :     # ubuntu(18.04 LTS)
        os_type_id = "4bfd5052-3c9c-11ed-8341-525400956326"
    elif os_type == "centos" :   # centos
        os_type_id = "abc"
    else:   # fedora(openstack default)
        os_type_id = "92a99cc2-5b57-48b9-9b2e-818c1e94d754"
    backup_template_id = registerCloudstackTemplate(zoneID, template_name, backup_img_file_name, os_type_id)    # 템플릿 등록 후 템플릿 id 받아옴
    instance_deploy_req_body = {"apiKey" : user_apiKey, "response" : "json", "command" : "deployVirtualMachine",
        "networkids" : cloudstack_user_network_id, "serviceofferingId" : medium_offeringID,
        'templateId': backup_template_id, "zoneId": zoneID,
        "displayname" : instance_name, "name" : instance_name, "domainid" : domainID,
        "account" : user_id, "hostid" : hostID, "startvm" : "true"
    }
    try :   # 클라우드스택 인스턴스 생성 시작
        print("인스턴스 생성 시작")
        instance_deploy_req = csc.requestThroughSig(user_secretKey, instance_deploy_req_body)
    except Exception as e:  # 생성 실패 에러 체크용, 인스턴스 생성 로직만 제대로 돌면 필요없는 부분
        print("에러 내용: ", e)
        return "클라우드스택에서 인스턴스 생성 시 에러 발생"
    
    while(True):        # 클라우드스택 인스턴스 생성됐는지 확인 및 생성된 인스턴스 정보 저장
        instance_info_req_body = {"apiKey" : user_apiKey, "response" : "json", "command" : "listVirtualMachines", "name" : instance_name}
        instance_info_req = csc.requestThroughSig(user_secretKey, instance_info_req_body)
        instance_info_res = json.loads(instance_info_req)
        
        if len(instance_info_res["listvirtualmachinesresponse"]) != 0:
            created_instance_id = instance_info_res["listvirtualmachinesresponse"]["virtualmachine"][0]["id"]
            created_instance_name = instance_info_res["listvirtualmachinesresponse"]["virtualmachine"][0]["name"]
            created_instance_status = instance_info_res["listvirtualmachinesresponse"]["virtualmachine"][0]["state"]
            created_instance_ip_address = "10.0.0." + str(CloudstackInstance.objects.filter(user_id=user_id_object.user_id).count() + 1)
            created_instance_image_id = instance_info_res["listvirtualmachinesresponse"]["virtualmachine"][0]["templateid"]
            created_instance_flavor_name = "MEDIUM"
            created_instance_ram_size = round(instance_info_res["listvirtualmachinesresponse"]["virtualmachine"][0]["memory"]/1024, 2)
            created_instance_disk_size = 5
            created_instance_num_cpu = instance_info_res["listvirtualmachinesresponse"]["virtualmachine"][0]["cpunumber"]
            break
        
        time.sleep(1)

    # db에 user_id, instance_id, image_id(template_id), ip_address, instance_name, status, flavor_name(medium 고정일 듯), ram_size(1G고정일 듯), disk_size, num_cpu 저장
    CloudstackInstance.objects.create(
        user_id = user_id_object,
        instance_id = created_instance_id,
        instance_pk = instance_pk,
        instance_name = created_instance_name,
        ip_address = created_instance_ip_address,
        status = "SHUTOFF",
        image_id = created_instance_image_id,
        flavor_name = created_instance_flavor_name,
        ram_size = created_instance_ram_size,
        disk_size = created_instance_disk_size,
        num_cpu = created_instance_num_cpu
    )
    log_manager.userLogAdder(user_id_object.user_id, created_instance_name, "Backuped(to cloudstack)", "instance")
    log_manager.instanceLogAdder(instance_pk, created_instance_name, "backup_complete", "Backuped(to cloudstack)")
    
    print("Created Instance " + backup_img_file_name + " to cloudstack")

    return "클라우드 스택으로 인스턴스 백업 완료"

def deleteCloudstackInstanceAndTemplate(admin_apiKey, admin_secretKey, instance_id, template_id):   # 이미 백업프로세스가 한 번이라도 진행됐을 경우 그 전에 존재하던 인스턴스, 템플릿 삭제 용
    import cloudstack_controller as csc

    instance_del_req_body = {"apiKey": admin_apiKey, "response": "json", "command": "destroyVirtualMachine",
        "id": instance_id, "expunge": "true"}
    instance_del_req = csc.requestThroughSig(admin_secretKey, instance_del_req_body)
    
    time.sleep(2)
    
    template_del_req_body = {"apiKey": admin_apiKey, "response": "json", "command": "deleteTemplate",
        "id": template_id}

    template_del_req = csc.requestThroughSig(admin_secretKey, template_del_req_body)
    
    return instance_del_req, template_del_req

# 이미 백업프로세스가 한 번이라도 진행됐을 경우 클라우드스택 인스턴스, 그 인스턴스에 쓰인 템플릿 삭제 후 다시 템플릿 등록 및 인스턴스 생성
def cloudstackInstanceDeleteAndCreate(user_id, cloudstack_user_apiKey, cloudstack_user_secretKey, backup_instance_pk, backup_instance_name, cloudstack_user_network_id, backup_img_file_name, backup_instance_os_type):
    import cloudstack_controller as csc
    admin_apiKey = csc.admin_apiKey
    admin_secretKey = csc.admin_secretKey

    if CloudstackInstance.objects.filter(instance_name=backup_instance_name).exists():  # In case of backup image exists, and cloudstack backup done.
        del_cloudstack_instance_info = CloudstackInstance.objects.get(instance_name=backup_instance_name)
        del_instance_id = del_cloudstack_instance_info.instance_id
        del_template_id = del_cloudstack_instance_info.image_id
        
        # 그 전에 생성됐던 백업본 삭제
        instance_del_req, template_del_req = deleteCloudstackInstanceAndTemplate(admin_apiKey, admin_secretKey, del_instance_id, del_template_id)
        print("클라우드스택의 백업본 인스턴스 삭제 리스폰스: ", instance_del_req, "\n클라우드스택의 백업본 템플릿 삭제 리스폰스: ", template_del_req)
        del_cloudstack_instance_info.delete()   # Delete instance information from Database

    time.sleep(5)   # 삭제하고 타이밍 얼마나 줄 지 생각해볼 것
    # 삭제 후 다시 템플릿 등록, 인스턴스 생성
    instance_backup_to_cloudstack_response = deployCloudstackInstance(user_id, cloudstack_user_apiKey, cloudstack_user_secretKey, backup_instance_pk, backup_instance_name, cloudstack_user_network_id, backup_img_file_name, backup_instance_os_type)

    return instance_backup_to_cloudstack_response

    # ------------------------------ Total Backup ------------------------------ #
def backup(cycle):
    import openstack_controller as oc                            # import는 여기 고정 -> 컴파일 시간에 circular import 때문에 걸려서
    openstack_hostIP = oc.hostIP

    print("this function runs every", cycle, "seconds")
    req_checker = RequestChecker()
    instance_tool = Instance()
    log_manager = InstanceLogManager()

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
            start_time = time.time()
            if instance.status == "ERROR" or instance.status == "RESTORING":
                print("instance " + instance.instance_name + " status is error. Can not backup.")
                continue
            print("인스턴스 오브젝트: ", instance)
            backup_instance_pk = instance.instance_pk   # 에러 터지면 이거 그냥 오브젝트로 바꾸기
            backup_instance_id = instance.instance_id
            backup_instance_name = instance.instance_name
            backup_instance_os_type = instance.os
            user_id = instance.user_id.user_id
            cloudstack_user_network_id = instance.user_id.cloudstack_network_id
            cloudstack_user_apiKey = instance.user_id.cloudstack_apiKey
            cloudstack_user_secretKey = instance.user_id.cloudstack_secretKey
            print("클라우드 스택의 유저 네트워크 id: ", cloudstack_user_network_id)
            print("인스턴스 id: ", backup_instance_id)
            log_manager.instanceLogAdder(backup_instance_pk, backup_instance_name, "backup_start", "Backup started(to cloudstack)")
            backup_payload = {
                "createBackup": {
                    "name": "Backup " + backup_instance_id,
                    "backup_type": "daily",
                    "rotation": 1
                }
            }
            if instance_tool.instance_image_uploading_checker(backup_instance_id) == True:  # instance snapshot create in progress
                print("Instance is image uploading state!!!")
                continue
            
            backup_req = req_checker.reqCheckerWithData("post", "http://" + openstack_hostIP + "/compute/v2.1/servers/" +
                backup_instance_id + "/action", admin_token,
                json.dumps(backup_payload))
            print("이미지 생성 request status code: ", backup_req.status_code)
            if backup_req == None:
                raise requests.exceptions.Timeout
            elif backup_req.status_code == 409:
                return "백업 이미지 생성 불가"

            instance_image_URL = backup_req.headers["Location"]
            print("image_URL : " + instance_image_URL)
            instance_image_ID = instance_image_URL.split("/")[6]
            print("image_ID : " + instance_image_ID)

            while(True):
                image_status_req = requests.get("http://" + openstack_hostIP + "/image/v2/images/" + instance_image_ID,  
                        headers = {"X-Auth-Token" : admin_token})     # 서버에 과부하 걸렸을 경우를 대비, 타임아웃 없는 요청으로.
                if image_status_req == None:
                    raise requests.exceptions.Timeout
                if image_status_req.status_code == 404:
                    return "오픈스택의 Image 용량이 가득 찼습니다."
                print("이미지 상태 조회 리스폰스: ", image_status_req.json())

                image_status = image_status_req.json()["status"]
                if image_status == "active":
                    break
                time.sleep(5)
            image_download_req = requests.get("http://" + openstack_hostIP + "/image/v2/images/" + instance_image_ID + "/file", 
                headers={'X-Auth-Token' : admin_token})
            if image_download_req == None:
                raise requests.exceptions.Timeout
            print("오픈스택에서의 이미지 다운로드에 대한 리스폰스: ", image_download_req)

            backup_img_file = open(backup_instance_id + ".qcow2", "wb")
            backup_img_file.write(image_download_req.content)
            backup_img_file.close()

            backup_img_del_req = req_checker.reqChecker("delete", "http://" + openstack_hostIP + "/image/v2/images/" + instance_image_ID, admin_token)  # For reason openstack Image container full, have to delete backup images
            print("Image used for backup delete response status code: ", backup_img_del_req.status_code)
            
            backup_img_file_name = backup_instance_id + ".qcow2"
            backup_img_file_to_db = open(backup_instance_id + ".qcow2", "rb")
            backup_image_data = {
                "instance_pk" : backup_instance_pk,     # 여기서 에러 터지면 instance 객체로 넣어주기
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
                    instance_backup_to_cloudstack_response = cloudstackInstanceDeleteAndCreate(user_id, cloudstack_user_apiKey, cloudstack_user_secretKey, backup_instance_pk, backup_instance_name, cloudstack_user_network_id, backup_img_file_name, backup_instance_os_type)
                    print("클라우드 스택으로의 백업 결과: ", instance_backup_to_cloudstack_response)
                    
                else:
                    print("Backup data not updated")
                    print(serializer.errors)
                    backup_img_file_to_db.close()
                    os.remove(backup_instance_id + ".qcow2")
                    print("Backup data not updated")
                    continue

                backup_img_file_to_db.close()
                print("updated")

            else:   # 백업을 해놓지 않은 경우(생성 후 한 번이라도 백업하고 업데이트 진행한 인스턴스 포함)
                if instance.update_image_ID != None:    # 생성 후 한 번이라도 백업하고 업데이트를 진행했을 경우, 업데이트 된 인스턴스 id에 매칭되는 백업 이미지가 존재하지 않아 백업이 안된 걸로 간주됨. 그에 따른 처리
                    update_image_id = instance.update_image_ID  # 업데이트 때 쓰인 이미지의 id
                    update_image_id_info_req = req_checker.reqChecker("get", "http://" + openstack_hostIP + "/image/v2/images/" + update_image_id, admin_token)
                    update_image_name = update_image_id_info_req.json()["name"] # 이미지의 id를 통해 name을 가져옴.("backup_for_update_업데이트 전 인스턴스 id" 의 형식)
                    before_update_instance_id = update_image_name[18:]    # 업데이트 전 instance의 id
                    if OpenstackBackupImage.objects.filter(instance_id=before_update_instance_id).exists():     # 업데이트 전 백업 이미지가 존재하는 경우 해당 백업본(백업 이미지, 클라우드스택 resources) 삭제 후 생성으로.
                        print("업데이트 전 백업되어있던 이미지를 삭제합니다. 이미지 ID: ", OpenstackBackupImage.objects.filter(instance_id=before_update_instance_id).image_id)
                        OpenstackBackupImage.objects.filter(instance_id=before_update_instance_id).delete()    # 해당 이미지 로컬에서 삭제
                        serializer = OpenstackBackupImageSerializer(data=backup_image_data)
                        if serializer.is_valid():
                            serializer.save()
                            print("Updated backup data info")
                            print(serializer.data)
                            backup_img_file_to_db.close()
                            os.remove(backup_instance_id + ".qcow2")

                            #------cloudstack instance expunge, template delete & template register, instance deploy------#
                            instance_backup_to_cloudstack_response = cloudstackInstanceDeleteAndCreate(user_id, cloudstack_user_apiKey, cloudstack_user_secretKey, backup_instance_pk, backup_instance_name, cloudstack_user_network_id, backup_img_file_name, backup_instance_os_type)
                            print("클라우드 스택으로의 백업 결과: ", instance_backup_to_cloudstack_response)
                            
                        else:
                            print("Backup data not updated")
                            print(serializer.errors)
                            backup_img_file_to_db.close()
                            os.remove(backup_instance_id + ".qcow2")
                            print("Backup data not updated")
                            continue

                        backup_img_file_to_db.close()
                        print("updated")

                    else:   # 업데이트 전 백업 이미지가 없는 경우, 그냥 생성으로.
                        serializer = OpenstackBackupImageSerializer(data=backup_image_data)
                        if serializer.is_valid():
                            serializer.save()
                            print("Saved Backup data info")
                            print(serializer.data)
                            backup_img_file_to_db.close()
                            os.remove(backup_instance_id + ".qcow2")
                            
                            #------cloudstack template register & instance deploy------#
                            instance_backup_to_cloudstack_response = deployCloudstackInstance(user_id, cloudstack_user_apiKey, cloudstack_user_secretKey, backup_instance_pk, backup_instance_name, cloudstack_user_network_id, backup_img_file_name, backup_instance_os_type)
                            print("클라우드 스택으로의 백업 결과: ", instance_backup_to_cloudstack_response)
                            
                        else:
                            print("Backup data not saved")
                            print(serializer.errors)
                            backup_img_file_to_db.close()                    
                            os.remove(backup_instance_id + ".qcow2")
                            print("Backup data not saved")
                            continue

                else:
                    serializer = OpenstackBackupImageSerializer(data=backup_image_data)
                    if serializer.is_valid():
                        serializer.save()
                        print("Saved Backup data info")
                        print(serializer.data)
                        backup_img_file_to_db.close()
                        os.remove(backup_instance_id + ".qcow2")
                        
                        #------cloudstack template register & instance deploy------#
                        instance_backup_to_cloudstack_response = deployCloudstackInstance(user_id, cloudstack_user_apiKey, cloudstack_user_secretKey, backup_instance_pk, backup_instance_name, cloudstack_user_network_id, backup_img_file_name, backup_instance_os_type)
                        print("클라우드 스택으로의 백업 결과: ", instance_backup_to_cloudstack_response)
                        
                    else:
                        print("Backup data not saved")
                        print(serializer.errors)
                        backup_img_file_to_db.close()                    
                        os.remove(backup_instance_id + ".qcow2")
                        print("Backup data not saved")
                        continue

            end_time = time.time()
            print("Backup to cloudstack time: ", f"{end_time - start_time:.5f} sec")
            print("Backup for " + backup_instance_id + " is completed")    
        
        return "All backup has completed."

    except OperationalError:
            return "인스턴스가 없습니다."
    except requests.exceptions.Timeout:
        return "오픈스택서버 고장"
    except requests.exceptions.ConnectionError:
            return "요청이 거부되었습니다."

# ------------------------------------------------------------ Restore Part ------------------------------------------------------------ #

    # --------------- For Instance Error --------------- #
def deleteStackBeforeRestore(tenant_id_for_restore, stack_id_for_del, stack_name_for_del, instance_update_image_id_for_del):    # 얘는 
    import openstack_controller as oc
    from openstack_controller import OpenstackServerError
    admin_token = oc.admin_token()
    openstack_hostIP = oc.hostIP
    req_checker = RequestChecker()

    del_instance_object = OpenstackInstance.objects.get(stack_id=stack_id_for_del)
    del_instance_id = del_instance_object.instance_id

    stack_del_req = req_checker.reqChecker("delete", "http://" + openstack_hostIP + "/heat-api/v1/" + tenant_id_for_restore + "/stacks/"    # 스택 삭제 요청
        + stack_name_for_del + "/" + stack_id_for_del, admin_token)
    if stack_del_req == None:
        raise OpenstackServerError
    
    if instance_update_image_id_for_del != None: # 업데이트를 한 번이라도 했을 시 업데이트에 쓰인 이미지도 삭제
        update_image_del_req = req_checker.reqChecker("delete", "http://" + openstack_hostIP + "/image/v2/images/" + instance_update_image_id_for_del, admin_token)
        print("업데이트에 쓰인 이미지 삭제 리스폰스: ", update_image_del_req)
        if update_image_del_req == None:
            raise OpenstackServerError
    
    while(True):    # 스택이 삭제됐는지 확인
        del_stack_status_req = req_checker.reqChecker("get", "http://" + openstack_hostIP + "/heat-api/v1/" + tenant_id_for_restore + "/stacks/" + stack_name_for_del + "/" + stack_id_for_del, admin_token)
        if del_stack_status_req.json()["stack"]["stack_status"] == "DELETE_COMPLETE":
            print("스택 " + stack_name_for_del + " 삭제 완료")
            break
        print("스택 삭제 중")
        time.sleep(2)

    if del_instance_object.instance_backup_img_file.filter(instance_id=del_instance_id).exists():   # 에러가 발생한 스택이 한 번이라도 백업 프로세스가 진행된 스택이라면
        del_backup_image_id = del_instance_object.instance_backup_img_file.get(instance_id=del_instance_id).image_id    # 그 백업 이미지 삭제
        backup_img_del_req = req_checker.reqChecker("delete", "http://" + oc.hostIP + "/image/v2/images/" + del_backup_image_id, admin_token)
        print("인스턴스의 백업 이미지 삭제 리스폰스: ", backup_img_del_req)
        if backup_img_del_req == None:
            raise OpenstackServerError

    print("에러가 발생해 삭제한 스택 이름: " + stack_name_for_del + "\n에러가 발생해 삭제한 스택 ID: " + stack_id_for_del)
    OpenstackInstance.objects.get(stack_id=stack_id_for_del).delete()   # 이 경우는 스택 정보를 db에서 날리는 것이므로 backup 이미지 정보도 db에서 사라짐.
    
    return "에러 발생한 스택 삭제 완료"


    # --------------- For Openstack Error --------------- #

def stopCloudstackInstance(cloudstack_user_apiKey, cloudstack_user_secretKey, instance_id):
    import cloudstack_controller as csc

    print("Stop Instance " + instance_id + " to cloudstack")
    request = {"apiKey" : cloudstack_user_apiKey, "response" : "json", "command" : "stopVirtualMachine",
        "id" : instance_id}
    instance_stop_req = csc.requestThroughSig(cloudstack_user_secretKey, request)
    print(instance_stop_req)

    return instance_stop_req

def getCloudstackVMStatus(cloudstack_user_apiKey, cloudstack_user_secretKey,instance_id):
    import cloudstack_controller as csc
    
    request = {"apiKey" : cloudstack_user_apiKey, "response" : "json", "command" : "listVirtualMachines",
        "id" : instance_id}
    print("get status Instance " + instance_id + " to cloudstack")
    instance_status_req = csc.requestThroughSig(cloudstack_user_secretKey, request)
    response = json.loads(instance_status_req)

    state = response["listvirtualmachinesresponse"]["virtualmachine"][0]["state"]
    print("VM state is ", state)

    return state

def listVolumesOfVM(cloudstack_user_apiKey, cloudstack_user_secretKey, instance_id):
    import cloudstack_controller as csc

    request = {"apiKey" : cloudstack_user_apiKey, "response" : "json", "command" : "listVolumes", "virtualmachineid" : instance_id}
    list_volume_req = csc.requestThroughSig(cloudstack_user_secretKey, request)
    print("volume list: ", list_volume_req)

    return list_volume_req

def getVolumeIDofVM(cloudstack_user_apiKey, cloudstack_user_secretKey, instance_id):
    res = listVolumesOfVM(cloudstack_user_apiKey, cloudstack_user_secretKey, instance_id)
    res_json=json.loads(res)

    instance_id=res_json['listvolumesresponse']['volume'][0]['id']
    print("volume is ", instance_id)

    return instance_id

def getOStypeIDofVM(cloudstack_user_apiKey, cloudstack_user_secretKey, vm_id):
    import cloudstack_controller as csc

    request = {"apiKey" : cloudstack_user_apiKey, "response" : "json", "command" : "listVirtualMachines",
        "id" : vm_id}
    response = csc.requestThroughSig(cloudstack_user_secretKey, request)
    response = json.loads(response)

    os_type_id = response["listvirtualmachinesresponse"]["virtualmachine"][0]["ostypeid"]
    print("VM os type id is ", os_type_id)

    return os_type_id

def createTemplate(cloudstack_user_apiKey, cloudstack_user_secretKey, template_name, os_type_id, volume_id):
    import cloudstack_controller as csc

    request = {"apiKey" : cloudstack_user_apiKey, "response" : "json", "command" : "createTemplate", "displaytext" : template_name,
        "name" : template_name, "ostypeid" : os_type_id, "volumeid" : volume_id}
    response = csc.requestThroughSig(cloudstack_user_secretKey,request)
    response_json = json.loads(response)

    template_id = response_json["createtemplateresponse"]["id"]
    print("Template Create is complete. id is ", template_id)

    return template_id

def updateTemplateExtractable(cloudstack_user_apiKey, cloudstack_user_secretKey, template_id):
    import cloudstack_controller as csc

    request = {"apiKey" : cloudstack_user_apiKey, "response" : "json", "command" : "updateTemplatePermissions",
        "id" : template_id, "isextractable" : "true"}
    response = csc.requestThroughSig(cloudstack_user_secretKey, request)

    return response

def extractTemplate(cloudstack_user_apiKey, cloudstack_user_secretKey, template_id):
    import cloudstack_controller as csc
    zone_id = csc.zoneID

    request_body = {"apiKey" : cloudstack_user_apiKey, "response" : "json", "command" : "extractTemplate",
        "id" : template_id, "mode" : "download", "zoneid" : zone_id}
    res = csc.requestThroughSigUsingRequests(cloudstack_user_secretKey, request_body)
    print(res)

    job_id = res["extracttemplateresponse"]["jobid"]
    print("job id is ", job_id)

    return job_id

def queryJobResult(cloudstack_user_apiKey,cloudstack_user_secretKey,extract_job_id):
    import cloudstack_controller as csc

    request = {"apiKey" : cloudstack_user_apiKey, "response" : "json", "command" : "queryAsyncJobResult", "jobid" : extract_job_id}
    response = csc.requestThroughSig(cloudstack_user_secretKey,request)
    print(response)

    return response

def getTemplateDownURL(cloudstack_user_apiKey,cloudstack_user_secretKey,extract_job_id):
    import cloudstack_controller as csc

    request = {"apiKey" : cloudstack_user_apiKey, "response" : "json", "command" : "queryAsyncJobResult", "jobid" : extract_job_id}
    response = csc.requestThroughSig(cloudstack_user_secretKey,request)
    resJson = json.loads(response)

    url = resJson['queryasyncjobresultresponse']['jobresult']['template']['url']
    url_split = url.split("/")
    url_split[2] = csc.hostIP + ":6050"
    down_url = "/".join(url_split)
    print("DownloadURL is : \n", down_url)

    return down_url

def getTemplateStatus(template_name):
    import cloudstack_controller as csc
    apiKey = csc.admin_apiKey
    secretKey = csc.admin_secretKey

    request = {}
    request['command'] = 'listTemplates'
    request['templatefilter'] = 'selfexecutable'
    request['name'] = template_name
    request['response'] = 'json'
    request['apikey'] = apiKey
    response = csc.requestThroughSig(secretKey, request)
    jsonData = json.loads(response)

    status = jsonData["listtemplatesresponse"]["template"][0]["status"]
    print("Template status is ", status)

    return status

def cloudstack_delete_VM(cloudstack_user_apiKey, cloudstack_user_secretKey, instance_id):
    import cloudstack_controller as csc

    request = {"apiKey" : cloudstack_user_apiKey, "response" : "json", "command" : "destroyVirtualMachine",
        "id" : instance_id, "expunge" : "true"}
    response = csc.requestThroughSig(cloudstack_user_secretKey, request)

    CloudstackInstance.objects.get(instance_id=instance_id).delete()    # DB에서 해당 VM 삭제

    return response

def cloudstack_delete_Template(cloudstack_user_apiKey, cloudstack_user_secretKey, template_id):
    import cloudstack_controller as csc

    request = {"apiKey" : cloudstack_user_apiKey, "response" : "json", "command" : "deleteTemplate",
        "id" : template_id}
    response = csc.requestThroughSig(cloudstack_user_secretKey, request)

    return response

def openstackImageUploader(template_name):
    import openstack_controller as oc  # import는 여기 고정 -> 컴파일 시간에 circular import 때문에 걸려서
    openstack_hostIP = oc.hostIP
    admin_token = oc.admin_token()
    req_checker = RequestChecker()

    image_create_payload = {
        "container_format": "bare",
        "disk_format": "qcow2",
        "name": template_name,
        "visibility": "public",
        "protected": False
    }
    create_req = req_checker.reqCheckerWithData("post", "http://" + openstack_hostIP + "/image/v2/images", admin_token, json.dumps(image_create_payload))
    if create_req == None:
        raise requests.exceptions.Timeout

    header = create_req.headers
    location = header["Location"]
    image_id = location.split("/")[5]
    print("Image ID : ", image_id)
    print("wait 5 seconds for upload binary data...")
    time.sleep(5)

    file = open(template_name + '.qcow2', 'rb')     # 클라우드스택으로부터 로컬에 다운받았던 파일 이용해서 이미지 생성
    contents = file.read()
    imageData_put_payload = contents

    put_req = requests.put("http://" + openstack_hostIP + "/image/v2/images/" + image_id + "/file", data=imageData_put_payload,     # req_checker는 header가 토큰으로 고정된 경우만 가능해서 이건 그냥 바로 요청
        headers={'X-Auth-Token' : admin_token, 'Content-type': 'application/octet-stream'})
    print("클라우드스택으로부터 추출한 오픈스택으로 이미지 업로드 리스폰스 코드: ", put_req.status_code)

    while(True):
        image_status_req = requests.get("http://" + openstack_hostIP + "/image/v2/images/" + image_id,  
            headers = {"X-Auth-Token" : admin_token})     # 서버에 과부하 걸렸을 경우를 대비, 타임아웃 없는 요청으로.
        if image_status_req.status_code == 404:
            return "오픈스택의 Image 용량이 가득 찼습니다."
        print("이미지 상태 조회 리스폰스: ", image_status_req.json())
        image_status = image_status_req.json()["status"]
        if image_status == "active":
            break
        time.sleep(2)

    file.close()
    os.remove(template_name + ".qcow2")     # 로컬에서 파일 삭제

    return "Uploaded image for restore to openstack"

def openstackStackCreate(instance_name, template_name):  # 오픈스택 상의 해당 이름의 스택을 삭제, 오픈스택에 올린 이미지를 토대로 다시 create
    import openstack_controller as oc
    from openstack_controller import OpenstackServerError
    req_checker = RequestChecker()
    template_modifier = TemplateModifier()
    stack_controller = Stack()
    admin_token = oc.admin_token()

    stack_object = OpenstackInstance.objects.get(instance_name=instance_name)
    user_id = stack_object.user_id.user_id
    user_password = stack_object.user_id.password
    tenant_id_for_restore = stack_object.user_id.openstack_user_project_id
    instance_id_for_del = stack_object.instance_id
    stack_id_for_del = stack_object.stack_id
    stack_name_for_del = stack_object.stack_name
    image_name_for_del = stack_object.image_name
    pc_spec = stack_object.pc_spec
    flavor = stack_object.flavor_name
    package = stack_object.package.split(",")
    os_of_instance = stack_object.os
    backup_time = stack_object.backup_time
    instance_update_image_id_for_del = stack_object.update_image_ID
    
    if stack_name_for_del != None:
        del_stack_before_restore_res = deleteStackBeforeRestore(tenant_id_for_restore, stack_id_for_del, stack_name_for_del, instance_update_image_id_for_del)     # 이전에 있던 스택 삭제
        print(del_stack_before_restore_res)
    else:   # In case instance is restored through freezer
        del_freezer_restored_instance_req = requests.delete("http://" + oc.hostIP + "/compute/v2.1/servers/" + instance_id_for_del,
            headers={'X-Auth-Token': admin_token})
        del_freezer_restore_image_id = requests.get("http://" + oc.hostIP + "/image/v2/images?name=" + image_name_for_del,
            headers={'X-Auth-Token': admin_token}).json()["images"][0]["id"]
        del_freezer_restore_image_req = requests.delete("http://" + oc.hostIP + "/image/v2/images/" + del_freezer_restore_image_id,
            headers={'X-Auth-Token': admin_token})
        print("Deleted freezer backuped instance", del_freezer_restored_instance_req.status_code, del_freezer_restore_image_req.status_code)
        OpenstackInstance.objects.get(instance_id=instance_id_for_del).delete()
    
    # ------------ 스택 재생성 로직 시작 ------------ #
    user_token = oc.user_token({"user_id" : user_id, "password" : user_password})

    if os_of_instance == "ubuntu":
        with open('templates/ubuntu_1804.json','r') as f:   # 오픈스택에 ubuntu 이미지 안올려놨음
            json_template_skeleton = json.load(f)
            json_template = template_modifier.templateModifyWhenServerRestored(template_name, json_template_skeleton, instance_name, flavor, package)
    elif os_of_instance == "centos":
        with open('templates/cirros.json','r') as f:    # 오픈스택에 centos 이미지 안올려놔서 일단 cirros.json으로
            json_template_skeleton = json.load(f)
            json_template = template_modifier.templateModifyWhenServerRestored(template_name, json_template_skeleton, instance_name, flavor, package)
    elif os_of_instance == "fedora":
        with open('templates/fedora.json','r') as f:    #이걸로 생성 test
            json_template_skeleton = json.load(f)
            json_template = template_modifier.templateModifyWhenServerRestored(template_name, json_template_skeleton, instance_name, flavor, package)
    
    #address heat-api v1 프로젝트 id stacks
    stack_req = req_checker.reqCheckerWithData("post", "http://" + oc.hostIP + "/heat-api/v1/" + tenant_id_for_restore + "/stacks",
        user_token, json_template)
    if stack_req == None:
        raise OpenstackServerError
    print("stack생성", stack_req.json())
    stack_id = stack_req.json()["stack"]["id"]

    stack_name_req = req_checker.reqChecker("get", "http://" + oc.hostIP + "/heat-api/v1/" + tenant_id_for_restore + "/stacks?id=" + stack_id,
        user_token)
    if stack_name_req == None:
        raise OpenstackServerError
    print("스택 이름 정보: ", stack_name_req.json())
    stack_name = stack_name_req.json()["stacks"][0]["stack_name"]

    instance_id, instance_name, instance_ip_address, instance_status, instance_image_name, instance_flavor_name, instance_ram_size, instance_disk_size, instance_num_cpu = stack_controller.stackResourceGetter("create", oc.hostIP, tenant_id_for_restore, stack_name, stack_id, user_token)
    package_for_db = (",").join(package)   # db에 패키지 목록 문자화해서 저장하는 로직
    
    instance_data = {   # db에 저장 할 인스턴스 정보
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
        "package" : package_for_db,
        "backup_time" : backup_time,
        "os" : os_of_instance
    }
    #serializing을 통한 인스턴스 정보 db 저장
    serializer = OpenstackInstanceSerializer(data=instance_data)
    if serializer.is_valid():
        serializer.save()
        print("Instance " + instance_name + " has restored from cloudstack to openstack!!")
        print(serializer.data)
    else:
        print("Restore from cloudstack to openstack of Instance " + instance_name + " has failed. ")
        print(serializer.errors)

    return "Restored Instance from cloudstack to openstack"

def restoreFromCloudstack(cloudstack_user_apiKey, cloudstack_user_secretKey, cloudstack_instance_id, cloudstack_instance_name, cloudstack_template_name, cloudstack_del_template_id):
    import cloudstack_controller as csc
    log_manager = InstanceLogManager()
    
    user_id = AccountInfo.objects.get(apiKey=cloudstack_user_apiKey).user_id
    instance_pk = CloudstackInstance.objects.get(instance_id=cloudstack_instance_id).instance_pk
    log_manager.instanceLogAdder(instance_pk, cloudstack_instance_name, "platform_restore_start", "Restore started(from cloudstack)")
    CloudstackInstance.objects.filter(instance_id=cloudstack_instance_id).update(status="RESTORING TO OPENSTACK")
    cloudstack_instance_stop_response = stopCloudstackInstance(cloudstack_user_apiKey, cloudstack_user_secretKey, cloudstack_instance_id)    # 실행중인 VM을 중지
    print(cloudstack_instance_stop_response)

    while True :
        VM_status = getCloudstackVMStatus(cloudstack_user_apiKey, cloudstack_user_secretKey, cloudstack_instance_id)
        if VM_status == "Stopped":
            break
        else :
            print("wait until VM status Stopped. current status is", VM_status)
            time.sleep(1)

    volume_id = getVolumeIDofVM(cloudstack_user_apiKey, cloudstack_user_secretKey, cloudstack_instance_id)    # VM으로부터 템플릿 생성
    os_type_id = getOStypeIDofVM(cloudstack_user_apiKey, cloudstack_user_secretKey, cloudstack_instance_id)
    template_name = cloudstack_template_name

    template_id = createTemplate(csc.admin_apiKey, csc.admin_secretKey, template_name, os_type_id, volume_id)
    time.sleep(10)

    while True:
        template_status = getTemplateStatus(template_name)
        if template_status == "Download Complete":
            break
        else:
            if template_status == "error":
                print("image status is error. terminate process.")
                exit()
            else:
                print("wait until image status active. current status is", template_status)
                time.sleep(3)

    update_template_extractable_response = updateTemplateExtractable(cloudstack_user_apiKey, cloudstack_user_secretKey, template_id)     # 템플릿을 extractable 상태로 업데이트
    print(update_template_extractable_response)

    extract_job_id = extractTemplate(cloudstack_user_apiKey, cloudstack_user_secretKey, template_id)      # 템플릿 extrat api 실행
    while True:
        job_status = queryJobResult(cloudstack_user_apiKey, cloudstack_user_secretKey, extract_job_id)
        job_status = json.loads(job_status)
        job_status = job_status["queryasyncjobresultresponse"]["jobstatus"]
        if job_status == 1:
            break
        else:
            print("wait until job status active. current status is", job_status)
            time.sleep(1)

    Cloudstack_Down_url = getTemplateDownURL(cloudstack_user_apiKey, cloudstack_user_secretKey, extract_job_id)     # 해당 extract job을 참조하여 download url 받아오기

    restore_res = requests.get(Cloudstack_Down_url)
    print("request get result : ",restore_res)

    file = open(template_name + '.qcow2', 'wb')
    file.write(restore_res.content)
    file.close()
    print("image file download response is", restore_res)

    image_upload_to_openstack = openstackImageUploader(template_name)   # 오픈스택에 이미지 올림
    print(image_upload_to_openstack)
    restore_stack_to_openstack = openstackStackCreate(cloudstack_instance_name, template_name)   # 오픈스택 상의 해당 이름의 스택을 삭제, 오픈스택에 올린 이미지를 토대로 다시 create
    print(restore_stack_to_openstack)

    del_cloudstack_VM_res = cloudstack_delete_VM(cloudstack_user_apiKey, cloudstack_user_secretKey, cloudstack_instance_id)
    print(del_cloudstack_VM_res)
    del_cloudstack_template_res = cloudstack_delete_Template(cloudstack_user_apiKey, cloudstack_user_secretKey, cloudstack_del_template_id)
    print(del_cloudstack_template_res)

    log_manager.userLogAdder(user_id, cloudstack_instance_name, "Restored(from cloudstack)", "instance")
    log_manager.instanceLogAdder(instance_pk, cloudstack_instance_name, "platform_restore_complete", "Restored(from cloudstack)")

    return restore_res

    # -------- Openstack Server Check Part -------- #
def openstackServerRecoveryChecker():
    import openstack_controller as oc
    log_manager = ServerLogManager()

    while True:
        if oc.admin_token() == None:      # TimeOut 발생시 계속 서버상태 체크
            print("openstack server not recovered")
            time.sleep(10)
            continue
                
        else:       # 오픈스택 서버가 정상화 되어 토큰 발급의 응답이 있을때는 restore 프로세스 수행 후 함수 종료
            accounts_list = AccountInfo.objects.all()
            for account in accounts_list:   # 모든 유저에 대해
                cloudstack_user_apiKey = account.cloudstack_apiKey
                cloudstack_user_secretKey = account.cloudstack_secretKey
                restore_cloudstack_instance_list = account.user_cloudstack_resource_info.all()
                for restore_cloudstack_instance in restore_cloudstack_instance_list:    # 유저의 모든 인스턴스에 대해
                    cloudstack_instance_id = restore_cloudstack_instance.instance_id
                    cloudstack_instance_name = restore_cloudstack_instance.instance_name
                    cloudstack_template_name = restore_cloudstack_instance.instance_name + "Template"
                    cloudstack_del_template_id = restore_cloudstack_instance.image_id
                    restore_res = restoreFromCloudstack(cloudstack_user_apiKey, cloudstack_user_secretKey, cloudstack_instance_id, cloudstack_instance_name, cloudstack_template_name, cloudstack_del_template_id)
                    print(restore_res)
            
            ServerStatusFlag.objects.filter(platform_name="openstack").update(status=True)
            log_manager.serverLogAdder("Openstack Server Recovered")

            return print("All User's Instance Recovered From Cloudstack!!")           

def openstackServerChecker():
    import openstack_controller as oc
    from openstack_controller import OpenstackServerError
    log_manager = ServerLogManager()

    if oc.admin_token() != None:
        print("Openstack Server On: ", ServerStatusFlag.objects.get(platform_name="openstack").status)
        return print("오픈스택 서버 정상")
    else:
        print("openstack server error occured")
        ServerStatusFlag.objects.filter(platform_name="openstack").update(status=False)
        log_manager.serverLogAdder("Openstack Server Error Occurred")
        try:
            restore_res = openstackServerRecoveryChecker()
        except OpenstackServerError as e:
            print("오픈스택 서버에 문제가 생겨 클라우드스택으로부터의 리스토어에 실패했습니다.")
            return e
        except Exception as e:
            print("클라우드스택으로부터 restore 중 예외 발생: ", e)
            return print("클라우드스택으로부터 restore 실패")

    return restore_res



# ------------------------------------------------------------ Freezer Backup and Restore ------------------------------------------------------------ #

def writeTxtFile(mode, instance_id):
    file = open("freezer_" + mode +"_template.txt", "w", encoding="UTF-8")
    file.write('source admin-openrc.sh')                         #환경에 맞게 설정해야됨 본인 리눅스 환경
    file.write('\nfreezer-agent --action ' + mode + ' --nova-inst-id ')
    file.write(instance_id)
    file.write(' --storage local --container /home/' + ssh_user_name + '/' + instance_id + '_backup' + ' --backup-name ' + instance_id + '_backup' + ' --mode nova --engine nova --no-incremental true --log-file ' + instance_id + '_' + mode+ '.log')
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
    server = ssh_ip_addr
    user = ssh_user_name
    pwd = ssh_password
    cli.connect(server, port=ssh_port, username=user, password=pwd)

    writeTxtFile("backup", instance_id)
    commandLines = readTxtFile("backup") # 메모장 파일에 적어놨던 명령어 텍스트 읽어옴
    print(commandLines)

    stdin, stdout, stderr = cli.exec_command(";".join(commandLines)) # 명령어 실행
    lines = stdout.readlines() # 실행한 명령어에 대한 결과 텍스트
    resultData = ''.join(lines)
    print(resultData) # 결과 확인
    cli.close()
    
    return resultData

def freezerRestore(instance_id):
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    server = ssh_ip_addr
    user = ssh_user_name
    pwd = ssh_password
    cli.connect(server, port=ssh_port, username=user, password=pwd)

    writeTxtFile("restore", instance_id)
    commandLines = readTxtFile("restore") # 메모장 파일에 적어놨던 명령어 텍스트 읽어옴
    print(commandLines)

    stdin, stdout, stderr = cli.exec_command(";".join(commandLines)) # 명령어 실행
    lines = stdout.readlines() # 실행한 명령어에 대한 결과 텍스트
    resultData = ''.join(lines)
    print(resultData) # 결과 확인
    cli.close()
    
    return resultData

def deleteStackBeforeFreezerRestore(tenant_id_for_restore, stack_id_for_del, stack_name_for_del, instance_update_image_id_for_del):
    import openstack_controller as oc
    token = oc.admin_token()
    openstack_hostIP = oc.hostIP
    req_checker = RequestChecker()

    del_instance_object = OpenstackInstance.objects.get(stack_id=stack_id_for_del)
    del_instance_id = del_instance_object.instance_id

    stack_del_req = req_checker.reqChecker("delete", "http://" + openstack_hostIP + "/heat-api/v1/" + tenant_id_for_restore + "/stacks/"    # 스택 삭제 요청
        + stack_name_for_del + "/" + stack_id_for_del, token)
    if stack_del_req == None:
        return "오픈스택 서버에 문제가 생겨 인스턴스(스택)을 삭제할 수 없습니다."
    
    if instance_update_image_id_for_del != None: # 업데이트를 한 번이라도 했을 시 업데이트에 쓰인 이미지도 삭제
        update_image_del_req = req_checker.reqChecker("delete", "http://" + openstack_hostIP + "/image/v2/images/" + instance_update_image_id_for_del, token)
        print("업데이트에 쓰인 이미지 삭제 리스폰스: ", update_image_del_req)
        if update_image_del_req == None:
            return "오픈스택 서버에 문제가 생겨 업데이트 때 사용한 이미지를 삭제할 수 없습니다."
    
    while(True):    # 스택이 삭제됐는지 확인
        del_stack_status_req = req_checker.reqChecker("get", "http://" + openstack_hostIP + "/heat-api/v1/" + tenant_id_for_restore + "/stacks/" + stack_name_for_del + "/" + stack_id_for_del, token)
        if del_stack_status_req.json()["stack"]["stack_status"] == "DELETE_COMPLETE":
            print("스택 " + stack_name_for_del + " 삭제 완료")
            break
        print("스택 삭제 중")
        time.sleep(2)

    print("에러가 발생해 삭제한 스택 이름: " + stack_name_for_del + "\n에러가 발생해 삭제한 스택 ID: " + stack_id_for_del)
    
    return "에러 발생한 스택 삭제 완료"

def freezerBackupWithCycle(cycle):
    import openstack_controller as oc
    log_manager = InstanceLogManager()
    
    instance_tool = Instance()
    print("freezerBackup With Cycle function Start!!")
    try:
        instance_count = OpenstackInstance.objects.filter(backup_time=cycle).count()
        if instance_count == 0:
            return "백업 주기 ", cycle, "시간짜리 instance 없음(freezer_backup_function)"

        backup_instance_list = OpenstackInstance.objects.filter(freezer_completed=True).filter(backup_time=cycle)       # 한 번 백업해뒀던 프리저 백업 파일을 오픈스택 VM에서 삭제하기 위한 로직
        print(cycle, "시간짜리 리스트(freezer_backup_function) that freezer backuped: ", backup_instance_list)
        if not backup_instance_list:
            print("리스트가 비어있음. 프리저 로컬 백업본 삭제 대상 없음.")
        else:
            for instance in backup_instance_list:
                if instance.status == "ERROR" or instance.status == "RESTORING":
                    print("instance " + instance.instance_name + " status is error. Can not backup with freezer.")
                    continue
                if instance_tool.instance_image_uploading_checker(instance.instance_id) == True:  # instance snapshot create in progress
                    print("Instance is image uploading state!!!")
                    continue
                print("인스턴스 오브젝트: ", instance)
                instance_id_for_OSremove = instance.instance_id
                print("인스턴스 id: ", instance_id_for_OSremove)

                #프리저 로컬 백업본 삭제 로직 시작
                try:
                    cli = paramiko.SSHClient()
                    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy)
                    server = ssh_ip_addr
                    user = ssh_user_name
                    pwd = ssh_password
                    cli.connect(server, port=ssh_port, username=user, password=pwd)
                    stdin, stdout, stderr = cli.exec_command("rm -rf " + instance_id_for_OSremove + "_backup")
                    print("리눅스 명령 수행 결과: ", ''.join(stdout.readlines()))
                    cli.close()
                except:
                    return "Error!! When removing freezer backup container!!"

                OpenstackInstance.objects.filter(instance_id=instance_id_for_OSremove).update(freezer_completed=False)

        backup_instance_list = OpenstackInstance.objects.filter(freezer_completed=False).filter(backup_time=cycle)
        for instance in backup_instance_list:
            start_time = time.time()    # 시간 측정용
            user_id = instance.user_id.user_id
            instance_pk = instance.instance_pk
            instance_name = instance.instance_name
            log_manager.instanceLogAdder(instance_pk, instance_name, "backup_start", "Backup started(with Freezer)")
            if instance.status == "ERROR" or  instance.status == "RESTORING":
                print("instance " + instance.instance_name + " status is error. Can not backup with freezer.")
                resultData = "Instance " + instance.instance_name + " Error"
                continue
            if instance_tool.instance_image_uploading_checker(instance.instance_id) == True:  # instance snapshot create in progress
                print("Instance is image uploading state!!!")
                continue
            print("인스턴스 오브젝트: ", instance)
            backup_instance_id = instance.instance_id
            print("인스턴스 id: ", backup_instance_id)

            try:
                resultData = freezerBackup(backup_instance_id)
                if resultData == "":
                    snapshot_of_freezer_id = requests.get("http://" + oc.hostIP + "/image/v2/images?name=snapshot_of_" + backup_instance_id, oc.admin_token).json()["images"][0]["id"]
                    snapshot_of_freezer_del_req = requests.delete("http://" + oc.hostIP + "/image/v2/images/" + snapshot_of_freezer_id, oc.admin_token)
                    print("Snapshot delete for reason fail of freezer backup, delete response: ", snapshot_of_freezer_del_req)
                    return resultData
            except:
                return "Error!! When trying freezer Backup"
            OpenstackInstance.objects.filter(instance_id=backup_instance_id).update(freezer_completed=True)
            log_manager.userLogAdder(user_id, instance_name, "Backuped(with Freezer)", "instance")
            log_manager.instanceLogAdder(instance_pk, instance_name, "backup_complete", "Backuped(with Freezer)")

            end_time = time.time()
            print("Freezer backup time: ", f"{end_time - start_time:.5f} sec")

        return "Freezer backup with cycle function ends."

    except OperationalError:
        return "인스턴스가 없습니다."

def freezerRestoreWithCycle():
    import time
    import openstack_controller as oc
    admin_token = oc.admin_token()
    req_checker = RequestChecker()
    log_manager = InstanceLogManager()

    print("freezerRestore function Start!!")
    error_instance_count = OpenstackInstance.objects.filter(status="ERROR").count()
    if error_instance_count == 0:
        return "Error 상태의 instance 없음"
    restore_instance_list = OpenstackInstance.objects.filter(status="ERROR").filter(freezer_completed=True)
    if restore_instance_list.count() == 0:
        return "Error 상태인 instance 중 프리저를 통해 백업 된 인스턴스가 없음"

    for restore_instance in restore_instance_list:  # 프리저로 백업됐고 에러가 난 인스턴스에 대해
        start_time = time.time()
        print("리스토어할 인스턴스 오브젝트: ", restore_instance)
        user_id = restore_instance.user_id.user_id
        instance_pk = restore_instance.instance_pk
        restore_instance_id = restore_instance.instance_id
        restore_instance_name = restore_instance.instance_name
        restore_instance_image_name = restore_instance.image_name
        OpenstackInstance.objects.filter(instance_id=restore_instance_id).update(status="RESTORING")
        log_manager.instanceLogAdder(instance_pk, restore_instance_name, "restore_start", "Restore started(with Freezer)")
        print("리스토어할 인스턴스 ID: ", restore_instance_id)

        # --------- error 터진 stack 삭제 --------- #
        del_stack_id = restore_instance.stack_id
        del_stack_name = restore_instance.stack_name
        del_update_image_id = restore_instance.update_image_ID
        del_openstack_tenant_id = restore_instance.user_id.openstack_user_project_id
        if del_stack_id != None:    # In case of error instance is not freezer backuped instance
            del_error_stack_result = deleteStackBeforeFreezerRestore(del_openstack_tenant_id, del_stack_id, del_stack_name, del_update_image_id)
            print(del_error_stack_result)
        else:
            del_freezer_restored_instance_req = requests.delete("http://" + oc.hostIP + "/compute/v2.1/servers/" + restore_instance_id,
                headers={'X-Auth-Token': admin_token})
            del_freezer_restore_image_id = requests.get("http://" + oc.hostIP + "/image/v2/images?name=" + restore_instance_image_name,
                headers={'X-Auth-Token': admin_token}).json()["images"][0]["id"]
            del_freezer_restore_image_req = requests.delete("http://" + oc.hostIP + "/image/v2/images/" + del_freezer_restore_image_id,
                headers={'X-Auth-Token': admin_token})
            print("Deleted freezer backuped instance", del_freezer_restored_instance_req.status_code, del_freezer_restore_image_req.status_code)

        # --------- freezer restore --------- #
        try:
            resultData = freezerRestore(restore_instance_id)
            print(resultData)
        except Exception as e:
            return "Error! When trying freezer restore " + restore_instance_id + "!!"

        while(True):
            error_instance_list_req = req_checker.reqChecker("get", "http://" + oc.hostIP + "/compute/v2.1/servers?name=" + restore_instance_name + "&status=ACTIVE", admin_token)
            if len(error_instance_list_req.json()["servers"]) != 0:
                restored_instance_id = error_instance_list_req.json()["servers"][0]["id"]
                restored_instance_name = error_instance_list_req.json()["servers"][0]["name"]
                print("freezer로 복구된 인스턴스 정보: ", restored_instance_id, restored_instance_name)
                instance_info_req = req_checker.reqChecker("get", "http://" + oc.hostIP + "/compute/v2.1/servers/" + restored_instance_id, admin_token)     #인스턴스 정보 get, 여기서 image id, flavor id 받아와서 다시 get 요청해서 세부 정보 받아와야 함
                if instance_info_req == None:
                    return "Error occurred when getting restored instance information!!!"
                print("인스턴스 정보: ", instance_info_req.json())
                restored_instance_ip_address = instance_info_req.json()["server"]["addresses"]["mainnetwork"][0]["addr"]
                break
            time.sleep(2)
        
        OpenstackInstance.objects.filter(instance_name=restored_instance_name).update(instance_id=restored_instance_id, instance_name=restored_instance_name,
            stack_id=None, stack_name=None, ip_address=restored_instance_ip_address, status="ACTIVE", image_name="RESTORE"+restored_instance_name, update_image_ID=None, freezer_completed=False)
        log_manager.userLogAdder(user_id, restore_instance_name, "Restored(with Freezer)", "instance")
        log_manager.instanceLogAdder(instance_pk, restore_instance_name, "restore_complete", "Restored(with Freezer)")

        end_time = time.time()
        print("Freezer restore time: ", f"{end_time - start_time:.5f} sec")

    return "Freezer restore functions ends."


def freezerBackup6():
    import openstack_controller as oc

    openstack_server_check = oc.admin_token()
    if openstack_server_check == None:
        return print("오픈스택 서버 문제 발생, Freezer Backup with cycle 6 불가")
    else:
        if ServerStatusFlag.objects.get(platform_name="openstack").status == True:
            freezer_backup_res = freezerBackupWithCycle(6)
            if freezer_backup_res == "":
                return print("Freezer backup Failed")
            print(freezer_backup_res)
        else:
            return print("오픈스택서버가 아직 복구되지 않았습니다.")

    return print("All Freezer Backup With 6 Hour Cycle Completed!!")

def freezerBackup12():
    import openstack_controller as oc

    openstack_server_check = oc.admin_token()
    if openstack_server_check == None:
        return print("오픈스택 서버 문제 발생, Freezer Backup with cycle 12 불가")
    else:
        if ServerStatusFlag.objects.get(platform_name="openstack").status == True:
            freezer_backup_res = freezerBackupWithCycle(12)
            if freezer_backup_res == "":
                return print("Freezer backup Failed")
            print(freezer_backup_res)
        else:
            return print("오픈스택서버가 아직 복구되지 않았습니다.")
    
    return print("All Freezer Backup With 12 Hour Cycle Completed!!")

def freezerRestore6():
    import openstack_controller as oc

    openstack_server_check = oc.admin_token()
    if openstack_server_check == None:
        return print("오픈스택 서버 문제 발생, Freezer Restore 불가")
    else:
        if ServerStatusFlag.objects.get(platform_name="openstack").status == True:
            errorCheckAndUpdateDBstatus()
            freezer_restore_res = freezerRestoreWithCycle()
            if freezer_restore_res != "All ERRORed instances restored!!":
                return print(freezer_restore_res)
            print(freezer_restore_res)
        else:
            return print("오픈스택서버가 아직 복구되지 않았습니다.")

    return print("All Freezer Restore Completed!!")

def backup6():
    import openstack_controller as oc

    openstack_server_check = oc.admin_token()
    if openstack_server_check == None:
        return print("오픈스택 서버 문제 발생, 주기 6시간짜리 백업 불가")
    else:
        if ServerStatusFlag.objects.get(platform_name="openstack").status == True:
            backup_res = backup(6)
            print(backup_res)
        else:
            return print("오픈스택서버가 아직 복구되지 않았습니다.")
    
    return print("All Backup With 6 Hour Cycle Completed!!")

def backup12():
    import openstack_controller as oc

    openstack_server_check = oc.admin_token()
    if openstack_server_check == None:
        return print("오픈스택 서버 문제 발생, 주기 12시간짜리 백업 불가")
    else:
        if ServerStatusFlag.objects.get(platform_name="openstack").status == True:
            backup_res = backup(12)
            print(backup_res)
        else:
            return print("오픈스택서버가 아직 복구되지 않았습니다.")

    return print("All Backup With 12 Hour Cycle Completed!!")

def backup_all6():
    DjangoServerTime.objects.filter(id=1).update(backup_ran=True)
    DjangoServerTime.objects.filter(id=1).update(backup_ran_time=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())))
    freezerBackup6()
    backup6()
    
def backup_all12():
    DjangoServerTime.objects.filter(id=1).update(backup_ran=True)
    DjangoServerTime.objects.filter(id=1).update(backup_ran_time=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())))
    freezerBackup12()
    backup12()


# ------------------------------------------------------------------------ Total Batch Job Part ------------------------------------------------------------------------ #
def start():
    import openstack_controller as oc
    backup_interval = oc.backup_interval
    scheduler = BackgroundScheduler() # ({'apscheduler.job_defaults.max_instances': 2}) # max_instance = 한 번에 실행할 수 있는 같은 job의 개수
    
    DjangoServerTime.objects.filter(id=1).update(start_time=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())))
    DjangoServerTime.objects.filter(id=1).update(backup_ran=False)
    scheduler.add_job(backup_all6, 'interval', seconds=backup_interval*60)
    scheduler.add_job(freezerRestore6, 'interval', seconds=30)
    scheduler.add_job(openstackServerChecker, 'interval', seconds=60)

    scheduler.start()