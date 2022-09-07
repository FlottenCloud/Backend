import os      #여기서 부터
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))    #여기까지는 상위 디렉토리 모듈 import 하기 위한 코드

import json
import requests
from rest_framework.views import APIView
from .models import OpenstackInstance


class TemplateModifier():
    

class RequestChecker():
    def reqCheckerWithData(self, method, req_url, req_header, req_data):
        try:
            if method == "post":
                req = requests.post(req_url,
                    headers = {'X-Auth-Token' : req_header},
                    data = req_data)
                return req

            elif method == "get":
                req = requests.get(req_url,
                    headers = {'X-Auth-Token' : req_header},
                    data = req_data)
                return req

            elif method == "put":
                req = requests.put(req_url,
                    headers = {'X-Auth-Token' : req_header},
                    data = req_data)
                return req

            elif method == "patch":
                req = requests.patch(req_url,
                    headers = {'X-Auth-Token' : req_header},
                    data = req_data)
                return req

            elif method == "delete":
                req = requests.delete(req_url,
                    headers = {'X-Auth-Token' : req_header},
                    data = req_data)
                return req

        except Exception:
            return None

    def reqChecker(self, method, req_url, req_header):
        try:
            if method == "post":
                req = requests.post(req_url,
                    headers = {'X-Auth-Token' : req_header})
                return req

            elif method == "get":
                req = requests.get(req_url,
                    headers = {'X-Auth-Token' : req_header})
                return req

            elif method == "put":
                req = requests.put(req_url,
                    headers = {'X-Auth-Token' : req_header})
                return req

            elif method == "patch":
                req = requests.patch(req_url,
                    headers = {'X-Auth-Token' : req_header})
                return req

            elif method == "delete":
                req = requests.delete(req_url,
                    headers = {'X-Auth-Token' : req_header})
                return req
            
        except Exception:
            return None



class Instance():    # 인스턴스 요청에 대한 공통 요소 클래스
    def checkDataBaseInstanceID(self, input_data):  # DB에서 Instance의 ID를 가져 오는 함수(request를 통해 받은 instance_id가 DB에 존재하는지 유효성 검증을 위해 존재)
        instance_id = input_data["instance_id"]
        try:
            instance_id = OpenstackInstance.objects.get(instance_id=instance_id).instance_id    # DB에 request로 받은 instance_id와 일치하는 instance_id가 있으면 instance_id 반환
        except :
            return None # DB에 일치하는 instance_id가 없으면 None(NULL) 반환

        return instance_id