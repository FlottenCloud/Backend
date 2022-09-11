import os   #여기서 부터
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))    #여기까지는 상위 디렉토리 모듈 import 하기 위한 코드

import openstack_controller as oc    #백엔드 루트 디렉토리에 openstack.py 생성했고, 그 안에 공통으로 사용될 함수, 변수들 넣을 것임. 아직은 클래스화 안 했음.
import cloudstack_controller as csc
import json
import requests
from .models import AccountInfo
from django.shortcuts import render
from django.views import View
from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response

openstack_hostIP = oc.hostIP
openstack_admin_project_id = oc.admin_project_id
openstack_admins_group_id = oc.admins_group_id
openstack_admin_role_id = oc.admin_role_id

cloudstack_hostIP = csc.hostIP
cloudstacK_api_base_url = csc.api_base_url
cloudstack_admin_apiKey = csc.admin_apiKey
cloudstack_admin_secretKey = csc.admin_secretKey

#회원가입 view
class AccountView(View):
    #회원등록 post 요청
    def post(self, cloudstack_account_make_req_body):
        input_data = json.loads(cloudstack_account_make_req_body.body)
        #------openstack user create------#
        admin_token = oc.admin_token()
        if admin_token == None:
            return JsonResponse({"message" : "오픈스택 관리자 토큰을 받아올 수 없습니다."}, status=404)

        # 사용자 생성 전 사용자 이름의 프로젝트 생성
        openstack_user_project_payload = {
            "project": {
                "domain_id" : "default",
                "name": "project_of_" + input_data["user_id"],
                "description": input_data["user_id"] + "'s project",
                "enabled": True,
            }
        }
        user_project_make_req = requests.post("http://" + openstack_hostIP + "/identity/v3/projects",
            headers={'X-Auth-Token': admin_token},
            data=json.dumps(openstack_user_project_payload))
        print(user_project_make_req.json())

        openstack_user_project_id = user_project_make_req.json()["project"]["id"]
        print("project_ID : ", openstack_user_project_id)

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
        openstack_user_make_req = requests.post("http://" + openstack_hostIP + "/identity/v3/users",
            headers={'X-Auth-Token': admin_token},
            data=json.dumps(openstack_user_payload))
        print(openstack_user_make_req.json())
        # openstack id 확인
        openstack_created_user_id = openstack_user_make_req.json()["user"]["name"]
        print(openstack_created_user_id)

        #사용자에게 프로젝트 역할 부여
        openstack_user_role_assignment_req = requests.put(
            "http://" + openstack_hostIP + "/identity/v3/projects/" + openstack_user_project_id + "/users/" + openstack_created_user_id + "/roles/" + openstack_admin_role_id,
            headers={'X-Auth-Token': admin_token})
        #생성된 사용자를 admins 그룹에 추가 # 일단 놔두기
        # group_res = requests.put(
        #     "http://" + openstack_hostIP + "/identity/v3/groups/" + openstack_admins_group_id + "/users/" + openstack_created_user_id,
        #     headers={'X-Auth-Token': admin_token})

        #------cloudstack user create------#
        cloudstack_account_make_req_body= {"apiKey" : cloudstack_admin_apiKey, "response" : "json", "command" : "createAccount", "accounttype" : "0",
            "email" : input_data["email"], "firstname" : input_data["first_name"], "lastname" : input_data["last_name"], 
            "password" : input_data["password"], "username" : input_data["user_id"]}    # account 생성 request
        cloudstacK_user_make_req = csc.requestThroughSig(cloudstack_admin_secretKey, cloudstack_account_make_req_body)
        cloudstacK_user_make_res = json.loads(cloudstacK_user_make_req)
        print("클라우드스택 유저 생성 response: ", cloudstacK_user_make_res)
        cloudstack_created_user_id = cloudstacK_user_make_res["createaccountresponse"]["account"]["user"][0]["id"]

        userKey_register_body={     # 생성된 account의 user_apiKey, user_secretKey 등록
            "apiKey" : cloudstack_admin_apiKey,
            "response" : "json",
            "command" : "registerUserKeys",
            "id" : cloudstack_created_user_id
        }
        secretKey = cloudstack_admin_secretKey
        userKey_register_req = csc.requestThroughSig(secretKey, userKey_register_body)
        userKey_register_res = json.loads(userKey_register_req)
        user_apiKey = userKey_register_res["registeruserkeysresponse"]["userkeys"]["apikey"]
        user_secretKey = userKey_register_res["registeruserkeysresponse"]["userkeys"]["secretkey"]

        #장고 ORM 업데이트
        AccountInfo.objects.create(
            user_id = input_data['user_id'],
            email = input_data['email'],
            password = input_data['password'],
            openstack_user_id = openstack_created_user_id,
            openstack_user_project_id = openstack_user_project_id,
            cloudstack_apiKey = user_apiKey,
            cloudstack_secretKey = user_secretKey
        )

        userKey_register_req = JsonResponse(input_data, status=200)
        userKey_register_req['Access-Control-Allow-Origin'] = '*'

        return userKey_register_req


    def get(self, request):                                   # 이건 아직 안썼는데 일단 나중에 제대로 수정할 것
        input_data = json.loads(request.body)
        admin_token = oc.admin_token()
        if admin_token == None:
            return JsonResponse({"message" : "오픈스택 관리자 토큰을 받아올 수 없습니다."})
        
        #Account_data = Account_info.objects.values()
        get_user_id = input_data["user_id"]
        Account_data_user_id = AccountInfo.objects.get(user_id = get_user_id)
        openstack_user_id = Account_data_user_id.openstack_user_id
        user_res = requests.get("http://" + openstack_hostIP + "/identity/v3/users/" + openstack_user_id,
            headers={'X-Auth-Token': admin_token})
        print(user_res.json())

        return JsonResponse({'account_info': user_res.json()}, status=200)


    def delete(self, request):  #그냥 api로 db랑 오픈스택에 유저 쌓인 거 정리하기 쉬우려고 만들었음. 후에 탈퇴기능 이용하려면 구현 제대로 할 것.
        input_data = json.loads(request.body)
        admin_token = oc.admin_token()
        if admin_token == None:
            return JsonResponse({"message" : "오픈스택 관리자 토큰을 받아올 수 없습니다."})
        del_user_id = input_data["user_id"]
        account_data = AccountInfo.objects.get(user_id = del_user_id)  #db에서 삭제할 유저 정보
        # print(account_data)
        del_project_id_openstack = account_data.openstack_user_project_id
        del_user_id_openstack = account_data.openstack_user_id  #해당 유저의 openstack user id
        # print(del_project_id_openstack)
        # print(del_user_id_openstack)
        user_resource = account_data.user_resource_info.all()   #해당 유저의 stack 정보(from 외래키 related name)

        for resource in user_resource:  # 오픈스택에서 user의 stack 모두 삭제
            stack_del_req = requests.delete("http://" + openstack_hostIP + "/heat-api/v1/" + del_project_id_openstack + "/stacks/"
                + resource.stack_name + "/" + resource.stack_id,
                headers = {'X-Auth-Token' : admin_token})
            print("스택 삭제 리스폰스: ", stack_del_req)
            if resource.update_image_ID != None:
                image_del_req = requests.delete("http://" + openstack_hostIP + "/image/v2/images/" + resource.update_image_ID,
                    headers = {'X-Auth-Token' : admin_token})
                print("업데이트에 쓰인 이미지 삭제 리스폰스: ", image_del_req)

        account_data.delete()
        project_del_req = requests.delete("http://" + openstack_hostIP + "/identity/v3/projects/" + del_project_id_openstack,
            headers={'X-Auth-Token': admin_token})     #오픈스택에 해당 프로젝트 삭제 request
        user_del_req = requests.delete("http://" + openstack_hostIP + "/identity/v3/users/" + del_user_id_openstack,
            headers={'X-Auth-Token': admin_token})     #오픈스택에 해당 유저 삭제 request
        #print(user_del_res.json())

        return HttpResponse("Delete Success")

#로그인 view
class SignView(View):
    #로그인 post 요청 
    def post(self, request):
        input_data = json.loads(request.body)
        # 사용자의 openstack 정보
        try:
            if AccountInfo.objects.filter(user_id=input_data['user_id']).exists():
                user = AccountInfo.objects.get(user_id=input_data['user_id'])
                if user.password == input_data['password']:
                    openstack_user_token = oc.user_token(input_data)
                    if openstack_user_token == None:
                        return JsonResponse({"message" : "오픈스택 유저 토큰을 받아올 수 없습니다."}, status=404)
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
            response = JsonResponse({'message': "서버에 존재하지 않는 사용자입니다."}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response