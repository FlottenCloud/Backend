import os   #여기서 부터
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))    #여기까지는 상위 디렉토리 모듈 import 하기 위한 코드

import openstack_controler as oc    #백엔드 루트 디렉토리에 openstack.py 생성했고, 그 안에 공통으로 사용될 함수, 변수들 넣을 것임. 아직은 클래스화 안 했음.
from django.shortcuts import render
import json
import requests
from .models import Account_info
from django.views import View
from django.http import HttpResponse, JsonResponse

openstack_hostIP = oc.hostIP
openstack_default_project_id = oc.project_id
openstack_admins_group_id = oc.group_id
openstack_admin_role_id = oc.role_id

#클라우드스택 key 추가해야 된다.
#회원가입 view
class AccountView(View):
    #회원등록 post 요청
    def post(self, request):
        input_data = json.loads(request.body)
        admin_token = oc.admin_token()

        # 사용자의 openstack 정보
        openstack_user_payload = {
            "user": {
                "name": input_data['user_id'],
                "password": str(input_data['password']),
                "default_project_id": openstack_default_project_id
            }
        }

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

        #장고 ORM 업데이트
        Account_info.objects.create(
            user_id=input_data['user_id'],
            email=input_data['email'],
            password=input_data['password'],
            openstack_user_id=openstack_created_user_id,
        )

        return response


    def get(self, request):                                              # instance list도 이런 식으로
        Account_data = Account_info.objects.values()

        return JsonResponse({'accounts': list(Account_data)}, status=200)


    def delete(self, request):  #그냥 api로 db랑 오픈스택에 유저 쌓인 거 정리하기 쉬우려고 만들었음.
        token = oc.admin_token()
        input_data = json.loads(request.body)
        del_user_id = input_data["user_id"]
        Account_data = Account_info.objects.get(user_id = del_user_id)  #db에서 해당 유저 삭제
        print(Account_data)
        del_user_id_openstack = Account_data.openstack_user_id  #해당 유저의 openstack user id
        print(del_user_id_openstack)
        Account_data.delete()
        user_del_res = requests.delete("http://" + openstack_hostIP + "/identity/v3/users/" + del_user_id_openstack,
            headers={'X-Auth-Token': token})     #오픈스택에 해당 유저 삭제 request
        #print(user_del_res.json())

        return HttpResponse("Delete Success")

#로그인 view
class SignView(View):
    #로그인 post 요청 
    def post(self, request):
        input_data = json.loads(request.body)
        # 사용자의 openstack 정보
        try:
            if Account_info.objects.filter(user_id=input_data['user_id']).exists():
                user = Account_info.objects.get(user_id=input_data['user_id'])
                if user.password == input_data['password']:
                    openstack_user_token = oc.user_token(input_data)
                    response = JsonResponse(
                        {"openstack_user_token" : openstack_user_token}, status=200
                    )

                    response['Access-Control-Allow-Origin'] = '*'
                    return response

                response = JsonResponse({'message': "비밀번호가 틀렸습니다."}, status=401)
                response['Access-Control-Allow-Origin'] = '*'
                return response

            response = JsonResponse({'message': "등록되지 않은 ID 입니다."}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        except KeyError:
            response = JsonResponse({'message': "ID와 비밀번호를 입력해주세요."}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response