import os   #여기서부터 장고와 환경을 맞추기 위한 import
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cloudmanager.settings")    # INSTALLED_APPS에 등록된 앱 내의 함수가 아니기 때문에, INSTALLED APPS에 있는 모듈을 임포트 할 때 필요
import django
django.setup()

import requests
import json
from django.http import JsonResponse

# from openstack.models import OpenstackInstance

<<<<<<< HEAD
hostIP = "119.198.160.6"    #김영후 집 데스크탑 공인 ip
admin_project_id = "33cba7ea48164446b6525331a99b985a" #김영후 데탑에 깔린 오픈스택 서버의 id들
admins_group_id = "3959c189d2bb4c5b8c9c938570e6087b"
admin_role_id = "f31482c34945485296c616c36c1fc2cb"

=======
hostIP = ""    #김영후 집 데스크탑 공인 ip     # 얘네들 학교에 깔린 오픈스택에 맞출 것
admin_project_id = "" #김영후 데탑에 깔린 오픈스택 서버의 id들
admins_group_id = ""
admin_role_id = ""
public_network_id = ""
>>>>>>> 767073b4badb1e91b51ff26f98c7f58d902e471d

class TokenExpiredError(Exception):
    def __init__(self):
        super().__init__("오픈스택의 토큰이 만료되었습니다.")

class OpenstackServerError(Exception):
    def __init__(self):
        super().__init__("오픈스택 서버에 문제가 생겼습니다.")

class OverSizeError(Exception):
    def __init__(self):
        super().__init__("인원 수 X 인원 당 예상 용량 값은 10G를 넘지 못합니다.")

def admin_token():  # admin user의 token을 발급받는 함수
    admin_token_payload = {   # admin user token 발급 Body
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
    try:
        auth_req = requests.post("http://" + hostIP + "/identity/v3/auth/tokens",
            headers = {'content-type' : 'application/json'},
            data = json.dumps(admin_token_payload),
            timeout = 5)

        admin_token = auth_req.headers["X-Subject-Token"]
        print("openstack admin token : ", admin_token) #디버깅 용, 나중에 지우기
    except requests.exceptions.Timeout:
        return None

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
    try:
        # Openstack keystone API를 통한 token 발급
        auth_req = requests.post("http://" + hostIP + "/identity/v3/auth/tokens",
            headers={'content-type': 'application/json'},
            data=json.dumps(user_token_payload),
            timeout = 5)
        # 발급받은 token 출력
        user_token = auth_req.headers["X-Subject-Token"]
        print("openstack user token : ", user_token)  #디버깅 용, 나중에 지우기
    except requests.exceptions.Timeout:
        return None

    return user_token

def getUserInfoByToken(user_token): # admin token과 웹으로부터 request header로 받은 user token을 통해 유저의 정보를 반환받는 함수
    admin_token_value = admin_token()   # admin token 발급
    if admin_token_value == None:
        return None
    
    try:
        auth_req = requests.get("http://" + hostIP + "/identity/v3/auth/tokens",
            headers={'X-Auth-Token': admin_token_value,
            "X-Subject-Token" : user_token},
            timeout = 5)
    except requests.exceptions.Timeout:
        return None

    return auth_req

def getUserID(user_token):  # admin token과 user token을 통해 반환받은 유저의 정보 중 user_id를 추출해내는 함수
    user_id_get = getUserInfoByToken(user_token)
    
    if user_id_get == None:
        return None
    
    if user_id_get.status_code == 401:
        raise TokenExpiredError
    
    user_id = user_id_get.json()["token"]["user"]["name"]

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