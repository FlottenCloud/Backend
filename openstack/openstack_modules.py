import os      #여기서 부터
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))    #여기까지는 상위 디렉토리 모듈 import 하기 위한 코드

import json
import requests
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
            flavor = "m1.tiny"  # test한다고 tiny 준거임.
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
            flavor = "m1.tiny"  # test한다고 tiny 준거임.
        elif 10 < disk_size :
            flavor = "EXCEEDED"

        # user_instance_name = input_data["instance_name"]
        backup_time = input_data["backup_time"]

        return user_package, flavor, backup_time, # user_os, user_instance_name

    def templateModify(self, template, user_id, user_instance_name, flavor, user_package):
        template_data = template
        template_data["stack_name"] = str(user_instance_name)   # 스택 name 설정
        template_data["template"]["resources"]["mybox"]["properties"]["name"] = str(user_instance_name) # 인스턴스 name 설정
        # template_data["template"]["resources"]["mybox"]["properties"]["flavor"] = flavor    # flavor 설정
        # template_data["template"]["resources"]["myconfig"]["properties"]["cloud_config"]["packages"] = user_package    # package 설정

        template_data["parameters"]["flavor"] = flavor    # flavor 설정
        template_data["parameters"]["packages"] = user_package    # package 설정

        template_data["template"]["resources"]["demo_key"]["properties"]["name"] = user_id + "_" + user_instance_name  # 키페어 name 설정
        template_data["template"]["resources"]["mynet"]["properties"]["name"] = user_id + "-net" + user_instance_name    # 네트워크 name 설정
        template_data["template"]["resources"]["mysub_net"]["properties"]["name"] = user_id + "-subnet" + user_instance_name # sub네트워크 name 설정
        template_data["template"]["resources"]["mysecurity_group"]["properties"]["name"] = user_id + "-security_group" + user_instance_name # 보안그룹 name 설정
        
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



class Instance:    # 인스턴스 요청에 대한 공통 요소 클래스
    def checkDataBaseInstanceID(self, input_data):  # DB에서 Instance의 ID를 가져 오는 함수(request를 통해 받은 instance_id가 DB에 존재하는지 유효성 검증을 위해 존재)
        instance_id = input_data["instance_id"]
        try:
            instance_id = OpenstackInstance.objects.get(instance_id=instance_id).instance_id    # DB에 request로 받은 instance_id와 일치하는 instance_id가 있으면 instance_id 반환
        except :
            return None # DB에 일치하는 instance_id가 없으면 None(NULL) 반환

        return instance_id