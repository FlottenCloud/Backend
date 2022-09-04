import os   #여기서부터 장고와 환경을 맞추기 위한 import
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cloudmanager.settings")    # INSTALLED_APPS에 등록된 앱 내의 함수가 아니기 때문에, INSTALLED APPS에 있는 모듈을 임포트 할 때 필요


django.setup()

import requests
import json
from django.http import JsonResponse

from openstack.models import OpenstackInstance

hostIP = "192.168.56.135"    #김영후 집 데스크탑 공인 ip
admin_project_id = "d19996ca7b054308bb26a469eae58d92" #김영후 데탑에 깔린 오픈스택 서버의 id들
admins_group_id = "0153b62c0e194a88b4cccaa7dcb50ff8"
admin_role_id = "fe20f13ea1ac4ee6b2f8883eb5b8b150"

def admin_token():  # admin user의 token을 발급받는 함수
    token_payload = {   # admin user token 발급 Body
        "auth": {
            "identity": {
                "methods": [
                    "password"
                ],
                "password": {
                    "user": {
                        "name": "admin",
                        "domain": {
                            "name": "Default"
                        },
                        "password": "0000"
                    }
                }
            }
        }
    }

    # Openstack keystone API를 통한 token 발급
    auth_req = requests.post("http://" + hostIP + "/identity/v3/auth/tokens",
        headers = {'content-type' : 'application/json'},
        data = json.dumps(token_payload))

    admin_token = auth_req.headers["X-Subject-Token"]
    print("openstack admin token : ", admin_token) #디버깅 용, 나중에 지우기

    return admin_token

def user_token(user_data):  # user의 토큰을 발급받는 함수
    user_token_payload = {  # user token 발급 Body
        "auth": {
            "identity": {
                "methods": [
                    "password"
                ],
                "password": {
                    "user": {
                        "name": user_data['user_id'],
                        "domain": {
                            "name": "Default"
                        },
                        "password": user_data['password']
                    }
                }
            }
        }
    }

    # Openstack keystone API를 통한 token 발급
    auth_req = requests.post("http://" + hostIP + "/identity/v3/auth/tokens",
                                headers={'content-type': 'application/json'},
                                data=json.dumps(user_token_payload))
    
    # 발급받은 token 출력
    print(auth_req.json())
    user_token = auth_req.headers["X-Subject-Token"]
    print("openstack user token : ", user_token)  #디버깅 용, 나중에 지우기

    return user_token

def getUserInfoByToken(user_token): # admin token과 웹으로부터 request header로 받은 user token을 통해 유저의 정보를 반환받는 함수
    #print("Before admin token")
    admin_token_value = admin_token()   # admin token 발급
    #print("getUserInfoByToken Start")
    # Openstack keystone API를 통한 token 발급
    auth_req = requests.get("http://" + hostIP + "/identity/v3/auth/tokens",
                                headers={'X-Auth-Token': admin_token_value,
                                "X-Subject-Token" : user_token}).json()
    print(auth_req)
    return auth_req

def getUserID(user_token):  # admin token과 user token을 통해 반환받은 유저의 정보 중 user_id를 추출해내는 함수
    user_id = getUserInfoByToken(user_token)["token"]["user"]["name"]

    return user_id

def getRequestParamsWithBody(request):  # 웹으로부터 request body가 있는 요청에 대해 admin token과 user token을 반환해주는 함수
    input_data = json.loads(request.body)   # header: user_token, Body: instance_id, system_num(스택 Create 시) 등등
    token = request.headers["X-Auth-Token"] # 웹에서 헤더로 실은 X-Auth-Token은 오픈스택에서는 user token임.
    user_id = getUserID(token)

    return input_data, token, user_id   # request로 받은 Body와 header로 받은 user token, token을 통해 정보를 얻어온 user ID를 반환

def getRequestParams(request):  # 웹으로부터 request body가 없는 요청에 대해 admin token과 user token을 반환해주는 함수
    token = request.headers["X-Auth-Token"] # 웹에서 헤더로 실은 X-Auth-Token은 오픈스택에서는 user token임.
    user_id = getUserID(token)

    return token, user_id   # request의 header로 받은 user token, token을 통해 정보를 얻어온 user ID를 반환

def checkDataBaseInstanceID(input_data):  # DB에서 Instance의 ID를 가져 오는 함수(request를 통해 받은 instance_id가 DB에 존재하는지 유효성 검증을 위해 존재)
    instance_id = input_data["instance_id"]

    try:
        instance_id = OpenstackInstance.objects.get(instance_id=instance_id).instance_id    # DB에 request로 받은 instance_id와 일치하는 instance_id가 있으면 instance_id 반환
    except :
        return None # DB에 일치하는 instance_id가 없으면 None(NULL) 반환

    return instance_id