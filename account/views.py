import os   #여기서 부터
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))    #여기까지는 상위 디렉토리 모듈 import 하기 위한 코드

import openstack_controller as oc    #백엔드 루트 디렉토리에 openstack.py 생성했고, 그 안에 공통으로 사용될 함수, 변수들 넣을 것임. 아직은 클래스화 안 했음.
import json
import requests
from .models import Account_info
from django.shortcuts import render
from django.views import View
from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response

openstack_hostIP = oc.hostIP
openstack_admin_project_id = oc.admin_project_id
openstack_admins_group_id = oc.admins_group_id
openstack_admin_role_id = oc.admin_role_id

#클라우드스택 key 추가해야 된다.
#회원가입 view
class AccountView(View):
    #회원등록 post 요청
    def post(self, request):
        input_data = json.loads(request.body)
        admin_token = oc.admin_token()

        # 사용자 생성 전 사용자 이름의 프로젝트 생성
        openstack_user_project_payload = {
            "project": {
                "domain_id" : "default",
                "name": "project_of_" + input_data["user_id"],
                "description": input_data["user_id"] + "'s project",
                "enabled": True,
            }
        }
        user_project_req = requests.post("http://" + openstack_hostIP + "/identity/v3/projects",
            headers={'X-Auth-Token': admin_token},
            data=json.dumps(openstack_user_project_payload))
        print(user_project_req.json())

        openstack_user_project_id = user_project_req.json()["project"]["id"]
        print("project_ID 1 : ", openstack_user_project_id)

        # 사용자의 openstack 정보
        openstack_user_payload = {
            "user": {
                "name": input_data['user_id'],
                "password": str(input_data['password']),
                "email": input_data["email"],
                "default_project_id": openstack_user_project_id
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

        #사용자에게 프로젝트 역할 부여
        role_assignment_req = requests.put(
            "http://" + openstack_hostIP + "/identity/v3/projects/" + openstack_user_project_id + "/users/" + openstack_created_user_id + "/roles/" + openstack_admin_role_id,
            headers={'X-Auth-Token': admin_token})

        #생성된 사용자를 admins 그룹에 추가
        # group_res = requests.put(
        #     "http://" + openstack_hostIP + "/identity/v3/groups/" + openstack_admins_group_id + "/users/" + openstack_created_user_id,
        #     headers={'X-Auth-Token': admin_token})
        #생성된 사용자에게 admin 역할 부여
        # permission_req = requests.put(
        #     "http://" + openstack_hostIP + "/identity/v3/domains/default/users/" + openstack_created_user_id + "/roles/" + openstack_admin_role_id)

        response = JsonResponse(input_data, status=200)
        response['Access-Control-Allow-Origin'] = '*'

        #장고 ORM 업데이트
        Account_info.objects.create(
            user_id = input_data['user_id'],
            email = input_data['email'],
            password = input_data['password'],
            openstack_user_id = openstack_created_user_id,
            openstack_user_project_id = openstack_user_project_id
            
        )

        return response


    def get(self, request):                                   # instance list도 이런 식으로
        input_data = json.loads(request.body)
        admin_token = oc.admin_token()
        #Account_data = Account_info.objects.values()
        get_user_id = input_data["user_id"]
        Account_data_user_id = Account_info.objects.get(user_id = get_user_id)
        openstack_user_id = Account_data_user_id.openstack_user_id
        user_res = requests.get("http://" + openstack_hostIP + "/identity/v3/users/" + openstack_user_id,
            headers={'X-Auth-Token': admin_token})
        print(user_res.json())

        return HttpResponse(user_res.json())#JsonResponse({'accounts': list(Account_data)}, status=200)


    def delete(self, request):  #그냥 api로 db랑 오픈스택에 유저 쌓인 거 정리하기 쉬우려고 만들었음.
        input_data = json.loads(request.body)
        token = oc.admin_token()
        del_user_id = input_data["user_id"]
        account_data = Account_info.objects.get(user_id = del_user_id)  #db에서 삭제할 유저 정보
        # print(account_data)
        del_project_id_openstack = account_data.openstack_user_project_id
        del_user_id_openstack = account_data.openstack_user_id  #해당 유저의 openstack user id
        # print(del_project_id_openstack)
        # print(del_user_id_openstack)
        user_resource = account_data.user_resource_info.all()   #해당 유저의 stack 정보

        for resource in user_resource:  # 오픈스택에서 user의 stack 모두 삭제
            stack_del_req = requests.delete("http://" + openstack_hostIP + "/heat-api/v1/" + del_project_id_openstack + "/stacks/"
            + resource.stack_name + "/" + resource.stack_id,
            headers = {'X-Auth-Token' : token})
            print(stack_del_req)

        account_data.delete()

        project_del_req = requests.delete("http://" + openstack_hostIP + "/identity/v3/projects/" + del_project_id_openstack,
            headers={'X-Auth-Token': token})     #오픈스택에 해당 프로젝트 삭제 request
        user_del_req = requests.delete("http://" + openstack_hostIP + "/identity/v3/users/" + del_user_id_openstack,
            headers={'X-Auth-Token': token})     #오픈스택에 해당 유저 삭제 request
        #print(user_del_res.json())
        #유저 삭제 시 -> 스택도 같이 삭제되지 않음.

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
                    #hash token 해줄 것
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
            response = JsonResponse({'message': "Openstack 서버에 존재하지 않는 사용자입니다."}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response