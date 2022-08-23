from django.shortcuts import render
import json
import requests
from .models import Account_info
from django.views import View
from django.http import HttpResponse, JsonResponse

openstack_hostIP = "119.198.160.6"
openstack_default_project_id = "f9bc10ab8e4040cdb173d33eeb25242b"
openstack_admins_group_id = "eec6e59ac9e6462a95932c51784d5e6a"
openstack_admin_role_id = "1cdb994001654362ad8c43b67a0ee825"

#클라우드스택 key 추가해야 된다.

#Admin 계정으로 token 발급
def token():
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
    auth_res = requests.post("http://" + openstack_hostIP + "/identity/v3/auth/tokens",
        headers = {'content-type' : 'application/json'},
        data = json.dumps(token_payload))

    #발급받은 token 출력
    admin_token = auth_res.headers["X-Subject-Token"]
    print("admin token : \n", admin_token)
    return admin_token



#회원가입 view
class AccountView(View):
    #회원등록 post 요청
    def post(self, request):
        input_data = json.loads(request.body)
        admin_token = token()

        # 사용자의 openstack 정보
        openstack_user_payload = {
            "user": {
                "name": input_data['user_id'],
                "password": str(input_data['password']),
                "default_project_id": openstack_default_project_id
            }
        }

        #장고 ORM 업데이트
        Account_info.objects.create(
            user_id=input_data['user_id'],
            email=input_data['email'],
            password=input_data['password'],
            #token=admin_token
            )

        #openstack 사용자 생성
        user_res = requests.post("http://" + openstack_hostIP + "/identity/v3/users",
                                 headers={'X-Auth-Token': admin_token},
                                 data=json.dumps(openstack_user_payload))
        print(user_res.json())

        # openstack id 확인
        openstack_created_user_id = user_res.json()["user"]["id"]
        print(openstack_created_user_id)

        #생성된 사용자를 admins 그룹에 추가
        group_res = requests.put(
            "http://" + openstack_hostIP + "/identity/v3/groups/" + openstack_admins_group_id + "/users/" + openstack_created_user_id,
            headers={'X-Auth-Token': admin_token})

        #생성된 사용자에게 admin 역할 부여
        permission_req = requests.put(
            "http://" + openstack_hostIP + "/identity/v3/domains/default/users/" + openstack_created_user_id + "/roles/" + openstack_admin_role_id)
        response = JsonResponse(input_data, status=200)
        response['Access-Control-Allow-Origin'] = '*'
        return response



    def get(self, request):                                              # instance list도 이런 식으로
        Account_data = Account_info.objects.values()
        return JsonResponse({'accounts': list(Account_data)}, status=200)


    def delete(self, request):
        Account_data = Account_info.objects.all()
        Account_data.delete()
        return HttpResponse("Delete Success")

#로그인 view
class SignView(View):
    #회원가입 후 생성된 사용자로 토큰 발급 함수
    def user_token(self, input_data):
        user_token_payload = {
            "auth": {
                "identity": {
                    "methods": [
                        "password"
                    ],
                    "password": {
                        "user": {
                            "name": input_data['user_id'],
                            "domain": {
                                "name": "Default"
                            },
                            "password": input_data['password']
                        }
                    }
                }
            }
        }
        # 새로 생성된 Openstack 사용자로 keystone token 발급
        auth_res = requests.post("http://" + openstack_hostIP + "/identity/v3/auth/tokens",
                                 headers={'content-type': 'application/json'},
                                 data=json.dumps(user_token_payload))
        # 발급받은 token 출력
        user_token = auth_res.headers["X-Subject-Token"]
        openstack_user_token = user_token
        print("openstack_user_token : ", openstack_user_token)
        return openstack_user_token


    #로그인 post 요청 
    def post(self, request):
        input_data = json.loads(request.body)
        # 사용자의 openstack 정보
        try:
            if Account_info.objects.filter(user_id=input_data['user_id']).exists():
                user = Account_info.objects.get(user_id=input_data['user_id'])
                if user.password == input_data['password']:
                    openstack_user_token = self.user_token(input_data)
                    response = JsonResponse(
                        {"openstack_user_token" : openstack_user_token}, status=200
                    )

                    response['Access-Control-Allow-Origin'] = '*'
                    return response

                response = JsonResponse({'message': "Wrong Password"}, status=401)
                response['Access-Control-Allow-Origin'] = '*'
                return response

            response = JsonResponse({'message': "Invalid name"}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        except KeyError:
            response = JsonResponse({'message': "INVALID_KEYS"}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response