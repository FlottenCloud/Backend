import os      #여기서 부터
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))    #여기까지는 상위 디렉토리 모듈 import 하기 위한 코드

import openstack_controller as oc
from openstack_controller import OpenstackServerError, InstanceNameNoneError, NumPeopleNegativeError, ExpectedDataSizeNegativeError, OverSizeError, StackUpdateFailedError, InstanceImageUploadingError, ImageFullError
import json
import requests
import time
from .models import OpenstackInstance, OpenstackBackupImage, DjangoServerTime
from account.models import AccountInfo
from cloudstack.models import CloudstackInstance

openstack_hostIP = oc.hostIP

class RequestChecker:
    def reqCheckerWithData(self, method, req_url, req_header, req_data):
        try:
            if method == "post":
                req = requests.post(req_url,
                    headers = {'X-Auth-Token' : req_header},
                    data = req_data,
                    timeout = 5)
                return req

            elif method == "get":
                req = requests.get(req_url,
                    headers = {'X-Auth-Token' : req_header},
                    data = req_data,
                    timeout = 5)
                return req

            elif method == "put":
                req = requests.put(req_url,
                    headers = {'X-Auth-Token' : req_header},
                    data = req_data,
                    timeout = 5)
                return req

            elif method == "patch":
                req = requests.patch(req_url,
                    headers = {'X-Auth-Token' : req_header},
                    data = req_data,
                    timeout = 5)
                return req

            elif method == "delete":
                req = requests.delete(req_url,
                    headers = {'X-Auth-Token' : req_header},
                    data = req_data,
                    timeout = 5)
                return req

        except requests.exceptions.Timeout:
            return None

    def reqChecker(self, method, req_url, req_header):
        try:
            if method == "post":
                req = requests.post(req_url,
                    headers = {'X-Auth-Token' : req_header},
                    timeout = 5)
                return req

            elif method == "get":
                req = requests.get(req_url,
                    headers = {'X-Auth-Token' : req_header},
                    timeout = 5)
                return req

            elif method == "put":
                req = requests.put(req_url,
                    headers = {'X-Auth-Token' : req_header},
                    timeout = 5)
                return req

            elif method == "patch":
                req = requests.patch(req_url,
                    headers = {'X-Auth-Token' : req_header},
                    timeout = 5)
                return req

            elif method == "delete":
                req = requests.delete(req_url,
                    headers = {'X-Auth-Token' : req_header},
                    timeout = 5)
                return req
            
        except requests.exceptions.Timeout:
            return None



class TemplateModifier:
    # 램, 디스크, 이미지, 네트워크 이름, 키페어 네임,
    def getUserRequirement(self, input_data):
        user_os = input_data["os"]
        user_package = input_data["package"]
        # if input_data["num_people"] < 0:
        #     raise NumPeopleNegativeError
        # if input_data["data_size"] < 0:
        #     raise ExpectedDataSizeNegativeError
        # disk_size = round(input_data["num_people"] * input_data["data_size"])   # flavor select에 쓰일 값
        user_pc_spec = input_data["pc_spec"]

        # if disk_size < 5:   # flavor select 로직
        #     flavor = "ds512M"
        # elif 5 <= disk_size <= 10:
        #     flavor = "ds1G"  # test한다고 tiny 준거임.
        # elif 10 < disk_size :
        #     flavor = "EXCEEDED"
        if user_pc_spec == "low":   # flavor select 로직
            flavor = "ds512M"
        elif user_pc_spec == "middle":
            flavor = "ds1G"  # test한다고 tiny 준거임.
        elif user_pc_spec == "high":
            flavor = "m1.small"

        user_instance_name = input_data["instance_name"]
        if user_instance_name == "":
            raise InstanceNameNoneError
        if OpenstackInstance.objects.filter(instance_name=user_instance_name).exists():
            user_instance_name = "Duplicated"
            
        backup_time = input_data["backup_time"]

        return user_os, user_package, user_pc_spec, flavor, user_instance_name, backup_time #input_data["num_people"], input_data["data_size"],

    def getUserUpdateRequirement(self, input_data):
        # user_os = input_data["os"]
        user_package = input_data["package"]
        user_pc_spec = input_data["pc_spec"]
        # if input_data["num_people"] < 0:
        #     raise NumPeopleNegativeError
        # if input_data["data_size"] < 0:
        #     raise ExpectedDataSizeNegativeError
        # disk_size = round(input_data["num_people"] * input_data["data_size"])   # flavor select에 쓰일 값
        
        # if disk_size < 5:   # flavor select 로직
        #     flavor = "ds512M"
        # elif 5 <= disk_size <= 10:
        #     flavor = "ds1G"  # test한다고 tiny 준거임.
        # elif 10 < disk_size :
        #     flavor = "EXCEEDED"

        if user_pc_spec == "low":   # flavor select 로직
            flavor = "ds512M"
        elif user_pc_spec == "middle":
            flavor = "ds1G"  # test한다고 tiny 준거임.
        elif user_pc_spec == "high":
            flavor = "m1.small"

        # user_instance_name = input_data["instance_name"]
        backup_time = input_data["backup_time"]

        return user_package, user_pc_spec, flavor, backup_time, # user_os, user_instance_name, input_data["num_people"], input_data["data_size"], 

    def templateModify(self, template, user_instance_name, flavor, user_package):
        template_data = template
        template_data["stack_name"] = str(user_instance_name)   # 스택 name 설정
        template_data["template"]["resources"]["mybox"]["properties"]["name"] = str(user_instance_name) # 인스턴스 name 설정
        template_data["parameters"]["flavor"] = flavor    # flavor 설정
        template_data["parameters"]["packages"] = user_package    # package 설정
        template_data["parameters"]["network_id"] = oc.public_network_id
        print(json.dumps(template_data))

        return(json.dumps(template_data))
    
    def templateModifyWhenRestored(self, backup_img_name, template, user_instance_name, flavor, user_package):
        template_data = template
        template_data["stack_name"] = str(user_instance_name)   # 스택 name 설정
        template_data["template"]["resources"]["mybox"]["properties"]["name"] = str(user_instance_name)# 인스턴스 name 설정
        template_data["parameters"]["image"] = backup_img_name  # 백업해놓은 이미지로 img 설정
        template_data["parameters"]["flavor"] = flavor    # flavor 설정
        template_data["parameters"]["packages"] = user_package    # package 설정
        template_data["parameters"]["network_id"] = oc.public_network_id
        
        print(json.dumps(template_data))

        return(json.dumps(template_data))

    def templateModifyWhenServerRestored(self, backup_img_name, template, user_instance_name, flavor, package):
        template_data = template
        template_data["stack_name"] = str(user_instance_name)   # 스택 name 설정
        template_data["template"]["resources"]["mybox"]["properties"]["name"] = str(user_instance_name)# 인스턴스 name 설정
        template_data["parameters"]["image"] = backup_img_name  # 백업해놓은 이미지로 img 설정
        template_data["parameters"]["flavor"] = flavor    # flavor 설정
        template_data["parameters"]["packages"] = package    # package 설정
        template_data["parameters"]["network_id"] = oc.public_network_id
        
        print(json.dumps(template_data))

        return(json.dumps(template_data))



class Instance(RequestChecker):    # 인스턴스 요청에 대한 공통 요소 클래스
    def checkDataBaseInstanceID(self, input_data):  # DB에서 Instance의 ID를 가져 오는 함수(request를 통해 받은 instance_id가 DB에 존재하는지 유효성 검증을 위해 존재)
        instance_pk = input_data["instance_pk"]
        try:
            instance_pk = OpenstackInstance.objects.get(instance_pk=instance_pk).instance_pk    # DB에 request로 받은 instance_id와 일치하는 instance_id가 있으면 instance_id 반환
        except :
            return None # DB에 일치하는 instance_id가 없으면 None(NULL) 반환

        return instance_pk
    
    
    def instance_image_uploading_checker(self, instance_id):
        image_uploading_check = super().reqChecker("get", "http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_id, oc.admin_token())
        is_image_uploading = image_uploading_check.json()["server"]["OS-EXT-STS:task_state"]
        if is_image_uploading == None:
            return False
        else:
            return True


    def exceedTimeCalculator(self, next_time, next_minute):
        if next_minute >= 60:
            next_time += (next_minute//60)
            next_minute -= (60*(next_minute//60))
            if next_minute < 10:
                next_minute = "0" + str(next_minute)
        if next_time < 10:
                next_time = "0" + str(next_time)
        return next_time, next_minute
    
    def timeFormatSetter(self, stack_data):
        if DjangoServerTime.objects.get(id=1).backup_ran == False:
            django_server_started_time = DjangoServerTime.objects.get(id=1).start_time[:16]
            next_time = int(django_server_started_time[11:13])
            next_minute = int(django_server_started_time[14:16]) + oc.backup_interval
            next_time, next_minute = self.exceedTimeCalculator(next_time, next_minute)
            print(next_time, next_minute)
            next_backup_time = django_server_started_time[:11] + str(next_time) + ":" + str(next_minute)
            stack_data["next_backup_time"] = next_backup_time
        else:
            django_server_backup_ran_time = DjangoServerTime.objects.get(id=1).backup_ran_time[:16]
            next_time = int(django_server_backup_ran_time[11:13])
            next_minute = int(django_server_backup_ran_time[14:16]) + oc.backup_interval
            next_time, next_minute = self.exceedTimeCalculator(next_time, next_minute)
            next_backup_time = django_server_backup_ran_time[:11] + str(next_time) + ":" + str(next_minute)
            stack_data["next_backup_time"] = next_backup_time
        
        return stack_data

    def instance_backup_time_show(self, stack_data, instance_pk):
        if CloudstackInstance.objects.filter(instance_pk=instance_pk).exists():
            stack_data["backup_completed_time"] = str(CloudstackInstance.objects.get(instance_pk=instance_pk).created_at)[:16]
            stack_data = self.timeFormatSetter(stack_data)
        else:
            stack_data["backup_completed_time"] = ""
            stack_data = self.timeFormatSetter(stack_data)
        return stack_data



class Stack(TemplateModifier, Instance):
    def stackResourceGetter(self, usage, openstack_hostIP, openstack_tenant_id, stack_name, stack_id, token):
        time.sleep(2)
        while(True):
            if usage == "update":
                while(True):
                    stack_status_req = requests.get("http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks?id=" + stack_id,  
                        headers = {"X-Auth-Token" : token})     # 서버에 과부하 걸렸을 경우를 대비, 타임아웃 없는 요청으로.
                    if stack_status_req == None:
                        return None
                    print(stack_status_req.json()["stacks"][0]["stack_status"])
                    if stack_status_req.json()["stacks"][0]["stack_status"] == "UPDATE_COMPLETE":
                        break
                    elif stack_status_req.json()["stacks"][0]["stack_status"] == "UPDATE_FAILED":
                        print("Stack update failed!")
                        raise StackUpdateFailedError
                    time.sleep(2)

            stack_resource_req = super().reqChecker("get", "http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks/" + stack_name + "/" # 스택으로 만든 인스턴스가 생성 완료될 때까지 기다림
                + stack_id + "/resources", token)
            if stack_resource_req == None:
                return None
            stack_resource = stack_resource_req.json()["resources"]

            for resource in stack_resource: # 스택 리스폰스에서 리소스들의 순서가 바뀌어 오는 경우 발견. 순회로 해결함.
                if resource["resource_type"] == "OS::Nova::Server":
                    print("리소스 정보: ", resource)
                    resource_instance = resource
                    break
            if resource_instance["resource_status"] == "CREATE_COMPLETE" or resource_instance["resource_status"] == "UPDATE_COMPLETE":
                instance_id = resource_instance["physical_resource_id"]
                print("인스턴스 CREATE 완료")
                break
            time.sleep(2)
        print("인스턴스 id: ", instance_id)
        time.sleep(1)
        
        instance_info_req = super().reqChecker("get", "http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_id, token)     #인스턴스 정보 get, 여기서 image id, flavor id 받아와서 다시 get 요청해서 세부 정보 받아와야 함
        if instance_info_req == None:
            return None
        print("인스턴스 정보: ", instance_info_req.json())

        instance_name = instance_info_req.json()["server"]["name"]
        print("인스턴스 이름: ", instance_name)
        instance_ip_address = instance_info_req.json()["server"]["addresses"]["mainnetwork"][0]["addr"]
        print("인스턴스 ip: ", instance_ip_address)
        instance_status =  instance_info_req.json()["server"]["status"]
        print("인스턴스 상태: ",instance_status)
        image_id = instance_info_req.json()["server"]["image"]["id"]
        flavor_id = instance_info_req.json()["server"]["flavor"]["id"]

        image_req = super().reqChecker("get", "http://" + openstack_hostIP + "/compute/v2.1/images/" + image_id, token)
        if image_req == None:
            return None
        instance_image_name = image_req.json()["image"]["name"]
        print("이미지 이름: ", instance_image_name)

        flavor_req = super().reqChecker("get", "http://" + openstack_hostIP + "/compute/v2.1/flavors/" + flavor_id, token)
        if flavor_req == None:
            return None
        print("flavor정보: ", flavor_req.json())

        instance_flavor_name = flavor_req.json()["flavor"]["name"]
        print("flavor 이름: ", instance_flavor_name)
        instance_ram_size = round(flavor_req.json()["flavor"]["ram"]/1024, 2)
        print("서버에서 넘겨주는 램 크기: ", flavor_req.json()["flavor"]["ram"])
        print("램 크기: ", instance_ram_size)
        instance_disk_size = flavor_req.json()["flavor"]["disk"]
        print("디스크 용량: ", instance_disk_size)
        instance_num_cpu = flavor_req.json()["flavor"]["vcpus"]
        print("CPU 개수: ", instance_num_cpu)

        return instance_id, instance_name, instance_ip_address, instance_status, instance_image_name, instance_flavor_name, instance_ram_size, instance_disk_size, instance_num_cpu


    def stackUpdater(self, openstack_hostIP, input_data, token, user_id):    
        update_openstack_tenant_id = AccountInfo.objects.get(user_id=user_id).openstack_user_project_id
        stack_data = OpenstackInstance.objects.get(instance_pk=input_data["instance_pk"])
        instance_id = stack_data.instance_id
        update_stack_id = stack_data.stack_id
        update_stack_name = stack_data.stack_name
        flavor_before_update = stack_data.flavor_name   # 요구사항 변경에 따른 플레이버가 변경되는지 체크용
        before_update_template_package = stack_data.package.split(",")
        image_used_for_update = stack_data.update_image_ID

        print("백업 전 패키지: ", before_update_template_package)

        user_req_package, updated_pc_spec, user_req_flavor, user_req_backup_time = super().getUserUpdateRequirement(input_data)
        # if user_req_flavor == "EXCEEDED":   # 용량이 10GB를 넘어간 경우
        #     raise OverSizeError
        if user_req_flavor == flavor_before_update:   # 원래 쓰려던 용량과 같은 범위 내의 용량을 요구사항으로 입력했을 경우
            user_req_flavor = "NOTUPDATE"
        else:
            if flavor_before_update == "ds1G" and user_req_flavor == "ds512M":  # 원래 쓰려던 용량보다 작은 용량을 요구사항으로 입력했을 경우
                user_req_flavor = "NOTUPDATE"
            elif flavor_before_update == "m1.small" and user_req_flavor == "ds512M":
                user_req_flavor = "NOTUPDATE"
            elif flavor_before_update == "m1.small" and user_req_flavor == "ds1G":
                user_req_flavor = "NOTUPDATE"
        package_for_update = list(set(user_req_package) - set(before_update_template_package))
        print("요청 정보: ", package_for_update, user_req_flavor, user_req_backup_time)
        
        if before_update_template_package[0] != "":
            package_origin_plus_user_req = before_update_template_package + package_for_update    # 기존 패키지 + 유저의 요청 패키지
            print("기존 패키지 + 유저의 요청 패키지: ", package_origin_plus_user_req)
        else:
            package_origin_plus_user_req = package_for_update
        package_for_db = (",").join(package_origin_plus_user_req)   # db에 저장할 패키지 목록 문자화

        
        if super().instance_image_uploading_checker(instance_id) == True:  # instance snapshot create in progress
            print("Instance is image uploading state!!!")
            raise InstanceImageUploadingError
        
        openstack_img_payload = { # 인스턴스의 스냅샷 이미지 만들기위한 payload
            "createImage": {
                "name": "backup_for_update_" + instance_id
            }
        }
        snapshot_req = super().reqCheckerWithData("post", "http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_id + "/action", 
            token, json.dumps(openstack_img_payload))
        if snapshot_req == None:
            raise OpenstackServerError
        print("인스턴스로부터 이미지 생성 리스폰스: ", snapshot_req)
        snapshotID_for_update = snapshot_req.headers["Location"].split("/")[6]
        print("image_ID : " + snapshotID_for_update)

        while(True):
            image_status_req = requests.get("http://" + openstack_hostIP + "/image/v2/images/" + snapshotID_for_update, 
                headers = {'X-Auth-Token' : token})     # 서버에 과부하 걸렸을 경우를 대비, 타임아웃 없는 요청으로.
            if image_status_req == None:
                raise OpenstackServerError
            elif image_status_req.status_code == 404:
                raise ImageFullError
            print("Image status request status code = ", image_status_req)
            print("이미지 상태 조회 리스폰스: ", image_status_req.json())

            image_status = image_status_req.json()["status"]
            if image_status == "active":
                break
            time.sleep(2)

        update_template = {   # 이미지와 요구사항을 반영한 템플릿 생성
            "parameters": {
                "image": "backup_for_update_" + instance_id
            }
        }
        if len(package_for_update) != 0:
            update_template["parameters"]["packages"] = package_for_update
        if user_req_flavor != "NOTUPDATE":
            update_template["parameters"]["flavor"] = user_req_flavor
        print("업데이트용 Template : ", json.dumps(update_template))

        stack_update_req = super().reqCheckerWithData("patch", "http://" + openstack_hostIP + "/heat-api/v1/" + update_openstack_tenant_id + "/stacks/" + update_stack_name + "/" + update_stack_id,
            token, json.dumps(update_template))
        if stack_update_req == None:
            raise OpenstackServerError
        print("stack 업데이트 결과: ", stack_update_req)
        print("stack 업데이트 결과 헤더: ", stack_update_req.headers)

        if image_used_for_update != None:
            image_used_for_update_del_req = super().reqChecker("delete", "http://" + openstack_hostIP + "/image/v2/images/" + image_used_for_update, token)
            if image_used_for_update_del_req == None:
                raise OpenstackServerError
            print("업데이트용 이미지의 이전 버전 삭제 요청 결과: ", image_used_for_update_del_req)

        try:
            updated_instance_id, updated_instance_name, updated_instance_ip_address, updated_instance_status, updated_instance_image_name, updated_instance_flavor_name, updated_instance_ram_size, updated_disk_size, updated_num_cpu = self.stackResourceGetter("update", openstack_hostIP, update_openstack_tenant_id, update_stack_name, update_stack_id, token)
        except Exception as e:  # stackResourceGetter에서 None이 반환 된 경우
            print("스택 정보 불러오는 중 예외 발생: ", e)
            raise OpenstackServerError
        
        return updated_instance_id, updated_instance_name, updated_instance_ip_address, updated_instance_status, updated_instance_image_name, updated_instance_flavor_name, updated_instance_ram_size, updated_disk_size, updated_num_cpu, package_for_db, updated_pc_spec, user_req_backup_time, snapshotID_for_update
    
    def stackUpdaterWhenFreezerRestored(self, openstack_hostIP, input_data, user_token, user_id):    # freezer로 restore 됐을 경우(stack_id, stack_name 없음)
        update_openstack_tenant_id = AccountInfo.objects.get(user_id=user_id).openstack_user_project_id
        stack_data = OpenstackInstance.objects.get(instance_pk=input_data["instance_pk"])
        instance_name = stack_data.instance_name
        instance_id = stack_data.instance_id
        instance_os = stack_data.os
        flavor_before_update = stack_data.flavor_name   # 요구사항 변경에 따른 플레이버가 변경되는지 체크용
        package_before_update = stack_data.package.split(",")

        user_req_package, updated_pc_spec, user_req_flavor, user_req_backup_time = super().getUserUpdateRequirement(input_data)
        # if user_req_flavor == "EXCEEDED":   # 용량이 10GB를 넘어간 경우
        #     raise OverSizeError
        if user_req_flavor == flavor_before_update:   # 원래 쓰려던 용량과 같은 범위 내의 용량을 요구사항으로 입력했을 경우
            user_req_flavor = "NOTUPDATE"
        else:
            if flavor_before_update == "ds1G" and user_req_flavor == "ds512M":  # 원래 쓰려던 용량보다 작은 용량을 요구사항으로 입력했을 경우
                user_req_flavor = "NOTUPDATE"
            elif flavor_before_update == "m1.small" and user_req_flavor == "ds512M":
                user_req_flavor = "NOTUPDATE"
            elif flavor_before_update == "m1.small" and user_req_flavor == "ds1G":
                user_req_flavor = "NOTUPDATE"

        if user_req_flavor == "NOTUPDATE":
            user_req_flavor = flavor_before_update
        package_for_update = list(set(user_req_package) - set(package_before_update))
        print("요청 정보: ", package_for_update, user_req_flavor, user_req_backup_time)

        if package_before_update[0] != "":
            package_origin_plus_user_req = package_before_update + package_for_update    # 기존 패키지 + 유저의 요청 패키지
        else:
            package_origin_plus_user_req = package_for_update
        package_for_db = (",").join(package_origin_plus_user_req)

        
        if super().instance_image_uploading_checker(instance_id) == True:  # instance snapshot create in progress
            print("Instance is image uploading state!!!")
            raise InstanceImageUploadingError
        
        openstack_img_payload = { # 인스턴스의 스냅샷 이미지 만들기위한 payload
            "createImage": {
                "name": "backup_for_update_" + instance_id
            }
        }
        snapshot_req = super().reqCheckerWithData("post", "http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_id + "/action", 
            user_token, json.dumps(openstack_img_payload))
        if snapshot_req == None:
            raise OpenstackServerError
        print("인스턴스로부터 이미지 생성 리스폰스: ", snapshot_req)
        freezer_restored_instance_snapshotID = snapshot_req.headers["Location"].split("/")[6]
        print("image_ID : " + freezer_restored_instance_snapshotID)

        while(True):
            image_status_req = requests.get("http://" + openstack_hostIP + "/image/v2/images/" + freezer_restored_instance_snapshotID, 
                headers = {"X-Auth-Token" : user_token})     # 서버에 과부하 걸렸을 경우를 대비, 타임아웃 없는 요청으로.
            if image_status_req == None:
                raise OpenstackServerError
            elif image_status_req.status_code == 404:
                raise ImageFullError
            print("이미지 상태 조회 리스폰스: ", image_status_req.json())

            image_status = image_status_req.json()["status"]
            if image_status == "active":
                break
            time.sleep(2)
        
        before_update_instance__del_req = super().reqChecker("delete", "http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_id, user_token)
        print("프리저로 복원된 인스턴스 삭제 리스폰스: ", before_update_instance__del_req)
        before_update_image_id_req = super().reqChecker("get", "http://" + openstack_hostIP + "/image/v2/images?name=" + "RESTORE" + instance_name, user_token)
        before_update_image_id = before_update_image_id_req.json()["images"][0]["id"]
        before_update_image_del_req = super().reqChecker("delete", "http://" + openstack_hostIP + "/image/v2/images/" + before_update_image_id, user_token)
        print("프리저로 복원된 인스턴스의 이미지 삭제 리스폰스: ", before_update_image_del_req)
        
        # stack create
        if instance_os == "ubuntu":
            with open('templates/ubuntu_1804.json','r') as f:  #backup_img_name, template, user_id, user_instance_name, flavor, package
                json_template_skeleton = json.load(f)
                json_template = super().templateModifyWhenRestored("backup_for_update_" + instance_id, json_template_skeleton, instance_name, user_req_flavor, package_for_update)
        elif instance_os == "centos":
            with open('templates/cirros.json','r') as f:    # 오픈스택에 centos 이미지 안올려놔서 일단 cirros.json으로
                json_template_skeleton = json.load(f)
                json_template = super().templateModifyWhenRestored("backup_for_update_" + instance_id, json_template_skeleton, instance_name, user_req_flavor, package_for_update)
        elif instance_os == "fedora":
            with open('templates/fedora.json','r') as f:    #이걸로 생성 test
                json_template_skeleton = json.load(f)
                json_template = super().templateModifyWhenRestored("backup_for_update_" + instance_id, json_template_skeleton, instance_name, user_req_flavor, package_for_update)

        stack_req = super().reqCheckerWithData("post", "http://" + openstack_hostIP + "/heat-api/v1/" + update_openstack_tenant_id + "/stacks",
            user_token, json_template)   # 스택 생성 요청
        if stack_req == None:
            raise OpenstackServerError
        print("stack생성", stack_req.json())
        stack_id = stack_req.json()["stack"]["id"]
        stack_name_req = super().reqChecker("get", "http://" + openstack_hostIP + "/heat-api/v1/" + update_openstack_tenant_id + "/stacks?id=" + stack_id,
            user_token)
        if stack_name_req == None:
            raise OpenstackServerError
        print("스택 이름 정보: ", stack_name_req.json())
        stack_name = stack_name_req.json()["stacks"][0]["stack_name"]

        try:    # 생성된 스택 정보
            updated_instance_id, updated_instance_name, updated_instance_ip_address, updated_instance_status, updated_instance_image_name, updated_instance_flavor_name, updated_instance_ram_size, updated_disk_size, updated_num_cpu = self.stackResourceGetter("create", openstack_hostIP, update_openstack_tenant_id, stack_name, stack_id, user_token)
        except Exception as e:  # stackResourceGetter에서 None이 반환 된 경우
            print("스택 정보 불러오는 중 예외 발생: ", e)
            raise OpenstackServerError

        return updated_instance_id, updated_instance_name, updated_instance_ip_address, updated_instance_status, updated_instance_image_name, updated_instance_flavor_name, updated_instance_ram_size, updated_disk_size, updated_num_cpu, package_for_db, updated_pc_spec, user_req_backup_time, freezer_restored_instance_snapshotID, stack_name, stack_id
