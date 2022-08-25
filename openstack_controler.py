import requests
import json

hostIP = "119.198.160.6"    #김영후 집 데스크탑 공인 ip
project_id = "f9bc10ab8e4040cdb173d33eeb25242b" #김영후 데탑에 깔린 오픈스택 서버의 id들
group_id = "eec6e59ac9e6462a95932c51784d5e6a"
role_id = "1cdb994001654362ad8c43b67a0ee825"

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
    # 발급받은 token 출력
    user_token = auth_res.headers["X-Subject-Token"]
    openstack_user_token = user_token
    print("openstack_user_token : ", openstack_user_token)  #디버깅 용, 나중에 지우기

    return openstack_user_token