from django.shortcuts import render
import json
import requests
from .models import Account_info
from django.views import View
from django.http import HttpResponse, JsonResponse
# Create your views here.

openstack_hostIP = "172.30.1.57"


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
    print("token : \n", admin_token)
    return admin_token




class AccountView(View):
    def post(self, request):
        input_data = json.loads(request.body)
        # admin_token = token()
        print("user create")
        Account_info.objects.create(
            user_id=input_data['user_id'],
            email=input_data['email'],
            password=input_data['password'],
            #token=admin_token
            )
        return HttpResponse("register success")


    def get(self, request):                                              # instance list도 이런 식으로
        Account_data = Account_info.objects.values()
        return JsonResponse({'accounts': list(Account_data)}, status=200)


    def delete(self, request):
        Account_data = Account_info.objects.all()
        Account_data.delete()
        return HttpResponse("Delete Success")

class SignView(View):
    def post(self, request):
        input_data = json.loads(request.body)
        # 사용자의 openstack 정보
        try:
            if Account_info.objects.filter(user_id=input_data['user_id']).exists():
                user = Account_info.objects.get(user_id=input_data['user_id'])
                if user.password == input_data['password']:

                    openstack_user_token = token()

                    response = JsonResponse(
                        {"openstack_user_token" : openstack_user_token}, status=200
                    )

                    response['Access-Control-Allow-Origin'] = '*'
                    return response

                response = HttpResponse("Wrong Password", status=401)
                response['Access-Control-Allow-Origin'] = '*'
                return response

            response = HttpResponse("Invalid name", status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        except KeyError:
            response = JsonResponse({'message': "INVALID_KEYS"}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response







        # token_payload = {
        #     "name": "admin",
        #     "password": "0000",
        #     "project_id": "d19996ca7b054308bb26a469eae58d92"  ## 프로젝트 ID 수정 필요
        # }
        #
        # auth_res = requests.post("http://52.78.82.160:7014/token",
        #                          headers={'content-type': 'application/json'},
        #                          data=json.dumps(token_payload))
        #
        # admin_token = auth_res.json()["token"]
        # print("token", admin_token)
        #
        # openstack_uesr_payload = {
        #     "user": {
        #         "name": input_data['name'],
        #         "password": str(input_data['password']),
        #         "default_project_id": "4b3afecefc7e4beaa1039d76e5e677d5"  ##프로젝트 ID 수정 필요
        #     }
        # }

        #36L ~~ 74L 은 클라우드스택 토큰 관련 코드 추가해야 됨, 모델도 수정 필요

        # 장고 ORM 에 추가
    #     Account_info.objects.create(
    #         name=input_data['name'],
    #         password=input_data['password'],
    #         token=admin_token
    #     )
    #
    #     # openstack 사용자 생성, ip 변경하기
    #     user_res = requests.post("http://164.125.70.22/identity/v3/users",
    #                              headers={'X-Auth-Token': admin_token},
    #                              data=json.dumps(openstack_uesr_payload))
    #     print(user_res.json())
    #
    #     # openstack id 확인
    #     openstack_id = user_res.json()["user"]["id"]
    #     # 생성된 사용자를 admins 그룹에 추가
    #     group_res = requests.put(
    #         "http://164.125.70.22/identity/v3/groups/245ee7dbac2d4a4fb60a872cbb0d3cd8/users/" + openstack_id,
    #         headers={'X-Auth-Token': admin_token})
    #
    #     permission_req = requests.put(
    #         "http://164.125.70.22/identity/v3/domains/default/users/" + openstack_id + "/roles/a72b87b6428c4a568b4116b2a500da9b")
    #     response = JsonResponse(input_data, status=200)
    #     response['Access-Control-Allow-Origin'] = '*'
    #     return response
    #
    # def get(self, request):
    #     Account_data = Account_info.objects.values()
    #     return JsonResponse({'accounts': list(Account_data)}, status=200)

    # def delete(self, request):
    #     Account_data = Account_info.objects.all()
    #     Account_data.delete()
    #     return HttpResponse("Delete Success")