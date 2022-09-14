import os      #여기서 부터
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))    #여기까지는 상위 디렉토리 모듈 import 하기 위한 코드

import json
import requests
import time
from .models import OpenstackInstance


class TemplateModifier:
    # 램, 디스크, 이미지, 네트워크 이름, 키페어 네임,
    def getUserRequirement(self, input_data):
        user_os = input_data["os"]
        user_package = input_data["package"]
        disk_size = round(input_data["num_people"] * input_data["data_size"])   # flavor select에 쓰일 값

        if disk_size < 5:   # flavor select 로직
            flavor = "ds512M"
        elif 5 <= disk_size <= 10:
            flavor = "ds1G"  # test한다고 tiny 준거임.
        elif 10 < disk_size :
            flavor = "EXCEEDED"

        user_instance_name = input_data["instance_name"]
        backup_time = input_data["backup_time"]

        return user_os, user_package, flavor, user_instance_name, backup_time

    def getUserUpdateRequirement(self, input_data):
        # user_os = input_data["os"]
        user_package = input_data["package"]
        disk_size = round(input_data["num_people"] * input_data["data_size"])   # flavor select에 쓰일 값
        
        if disk_size < 5:   # flavor select 로직
            flavor = "ds512M"
        elif 5 <= disk_size <= 10:
            flavor = "ds1G"  # test한다고 tiny 준거임.
        elif 10 < disk_size :
            flavor = "EXCEEDED"

        # user_instance_name = input_data["instance_name"]
        backup_time = input_data["backup_time"]

        return user_package, flavor, backup_time, # user_os, user_instance_name

    def templateModify(self, template, user_id, user_instance_name, flavor, user_package):
        template_data = template
        template_data["stack_name"] = str(user_instance_name)   # 스택 name 설정
        template_data["template"]["resources"]["mybox"]["properties"]["name"] = str(user_instance_name) # 인스턴스 name 설정
        template_data["template"]["resources"]["demo_key"]["properties"]["name"] = user_id + "_" + user_instance_name  # 키페어 name 설정
        template_data["template"]["resources"]["mynet"]["properties"]["name"] = user_id + "-net" + user_instance_name    # 네트워크 name 설정
        template_data["template"]["resources"]["mysub_net"]["properties"]["name"] = user_id + "-subnet" + user_instance_name # sub네트워크 name 설정
        template_data["template"]["resources"]["mysecurity_group"]["properties"]["name"] = user_id + "-security_group" + user_instance_name # 보안그룹 name 설정
        template_data["parameters"]["flavor"] = flavor    # flavor 설정
        template_data["parameters"]["packages"] = user_package    # package 설정
        print(json.dumps(template_data))

        return(json.dumps(template_data))
    
    def templateModifyWhenRestore(self, backup_img_name, template, user_id, user_instance_name, flavor):
        template_data = template
        template_data["stack_name"] = str(user_instance_name)   # 스택 name 설정
        template_data["template"]["resources"]["mybox"]["properties"]["name"] = str(user_instance_name)# 인스턴스 name 설정
        template_data["template"]["resources"]["demo_key"]["properties"]["name"] = user_id + "_" + user_instance_name  # 키페어 name 설정
        template_data["template"]["resources"]["mynet"]["properties"]["name"] = user_id + "-net" + user_instance_name    # 네트워크 name 설정
        template_data["template"]["resources"]["mysub_net"]["properties"]["name"] = user_id + "-subnet" + user_instance_name # sub네트워크 name 설정
        template_data["template"]["resources"]["mysecurity_group"]["properties"]["name"] = user_id + "-security_group" + user_instance_name # 보안그룹 name 설정
        template_data["parameters"]["image"] = backup_img_name  # 백업해놓은 이미지로 img 설정
        template_data["parameters"]["flavor"] = flavor    # flavor 설정
        
        print(json.dumps(template_data))

        return(json.dumps(template_data))

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


class Stack(RequestChecker):
    def stackResourceGetter(self, usage, openstack_hostIP, openstack_tenant_id, user_id, stack_name, stack_id, token):
        time.sleep(3)
        while(True):
            if usage == "update":
                while(True):
                    stack_status_req = super().reqChecker("get", "http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks?id=" + stack_id, token)
                    if stack_status_req == None:
                        return None
                    print(stack_status_req.json()["stacks"][0]["stack_status"])
                    if stack_status_req.json()["stacks"][0]["stack_status"] == "UPDATE_COMPLETE":
                        break
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
            if resource_instance["resource_status"] == "CREATE_COMPLETE":
                instance_id = resource_instance["physical_resource_id"]
                print("인스턴스 CREATE 완료")
                break
            time.sleep(2)

        print("인스턴스 id: ", instance_id)

        time.sleep(1)
        #인스턴스 정보 get, 여기서 image id, flavor id 받아와서 다시 get 요청해서 세부 정보 받아와야 함
        instance_info_req = super().reqChecker("get", "http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_id, token)
        if instance_info_req == None:
            return None
        print("인스턴스 정보: ", instance_info_req.json())

        instance_name = instance_info_req.json()["server"]["name"]
        print("인스턴스 이름: ", instance_name)
        instance_ip_address = instance_info_req.json()["server"]["addresses"][user_id + "-net" + instance_name][0]["addr"]
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


class Instance:    # 인스턴스 요청에 대한 공통 요소 클래스
    def checkDataBaseInstanceID(self, input_data):  # DB에서 Instance의 ID를 가져 오는 함수(request를 통해 받은 instance_id가 DB에 존재하는지 유효성 검증을 위해 존재)
        instance_id = input_data["instance_id"]
        try:
            instance_id = OpenstackInstance.objects.get(instance_id=instance_id).instance_id    # DB에 request로 받은 instance_id와 일치하는 instance_id가 있으면 instance_id 반환
        except :
            return None # DB에 일치하는 instance_id가 없으면 None(NULL) 반환

        return instance_id