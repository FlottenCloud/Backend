import requests
import json
from django.http import JsonResponse

from openstack.models import OpenstackInstance

hostIP = "119.198.160.6"    #김영후 집 데스크탑 공인 ip
admin_project_id = "f9bc10ab8e4040cdb173d33eeb25242b" #김영후 데탑에 깔린 오픈스택 서버의 id들
admins_group_id = "eec6e59ac9e6462a95932c51784d5e6a"
admin_role_id = "1cdb994001654362ad8c43b67a0ee825"

def admin_token():
    # Admin으로 Token 발급 Body
    token_payload = {
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

    # Openstack keystone token 발급
    auth_res = requests.post("http://" + hostIP + "/identity/v3/auth/tokens",
        headers = {'content-type' : 'application/json'},
        data = json.dumps(token_payload))

    #발급받은 token 출력
    admin_token = auth_res.headers["X-Subject-Token"]
    print("token : \n",admin_token) #디버깅 용, 나중에 지우기

    return admin_token

def user_token(user_data):
    user_token_payload = {
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
    # 새로 생성된 Openstack 사용자로 keystone token 발급
    auth_res = requests.post("http://" + hostIP + "/identity/v3/auth/tokens",
                                headers={'content-type': 'application/json'},
                                data=json.dumps(user_token_payload))
    print("abc")
    #print(auth_res.body)
    # 발급받은 token 출력
    user_token = auth_res.headers["X-Subject-Token"]
    openstack_user_token = user_token
    print("openstack_user_token : ", openstack_user_token)  #디버깅 용, 나중에 지우기

    return openstack_user_token

def getInfoByToken(user_token):
    admin_token_value = admin_token()
    auth_res = requests.get("http://" + hostIP + "/identity/v3/auth/tokens",
                                headers={'X-Auth-Token': admin_token_value,
                                "X-Subject-Token" : user_token}).json()
    return auth_res

def getUserID(user_token):
    user_id = getInfoByToken(user_token)["token"]["user"]["name"]
    return user_id

def getRequestParamsWithBody(request):
    input_data = json.loads(request.body)   # user_id, password
    token = request.headers["X-Auth-Token"]#oc.user_token(input_data)
    user_id = getUserID(token)

    return input_data, token, user_id

def getRequestParams(request):
    token = request.headers["X-Auth-Token"]#oc.user_token(input_data)
    user_id = getUserID(token)

    return token, user_id

def getInstanceID(input_data):
    instance_id = input_data["instance_id"]
    try:
        instance_id = OpenstackInstance.objects.get(instance_id=instance_id).instance_id
    except :
        return None

    return instance_id