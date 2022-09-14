import os   #여기서 부터
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))    #여기까지는 상위 디렉토리 모듈 import 하기 위한 코드

import openstack_controller as oc    #백엔드 루트 디렉토리에 openstack.py 생성했고, 그 안에 공통으로 사용될 함수, 변수들 넣을 것임. 아직은 클래스화 안 했음.
import cloudstack_controller as csc
import time
import json
import requests
from .models import AccountInfo
from django.db.models import Max
from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from rest_framework.views import APIView
from drf_yasg.utils       import swagger_auto_schema
from .serializers import UserDeleteSerializer, UserRegisterSerializer, UserSignInSerializer

openstack_hostIP = oc.hostIP
openstack_admin_project_id = oc.admin_project_id
openstack_admins_group_id = oc.admins_group_id
openstack_admin_role_id = oc.admin_role_id

cloudstack_hostIP = csc.hostIP
cloudstacK_api_base_url = csc.api_base_url
cloudstack_admin_apiKey = csc.admin_apiKey
cloudstack_admin_secretKey = csc.admin_secretKey
cloudstack_netOfferingID = csc.netOfferingID_L2VLAN
cloudstack_zoneID = csc.zoneID
cloudstack_domainID = csc.domainID


class AccountView(APIView):
    @swagger_auto_schema(tags=["User Register API"], request_body=UserRegisterSerializer, responses={200:"Success", 404:"Not Found"})
    def post(self, cloudstack_account_make_req_body):
        input_data = json.loads(cloudstack_account_make_req_body.body)
        #------openstack user create------#
        admin_token = oc.admin_token()
        if admin_token == None:
            return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 회원가입을 진행할 수 없습니다."}, status=404)

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
        openstack_created_user_id = openstack_user_make_req.json()["user"]["id"]
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
        cloudstack_account_make_req_body= {"apiKey" : cloudstack_admin_apiKey, "response" : "json", "command" : "createAccount", "accounttype" : "1",
            "email" : input_data["email"], "firstname" : input_data["first_name"], "lastname" : input_data["last_name"], 
            "password" : input_data["password"], "username" : input_data["user_id"]}    # account 생성 request
        cloudstacK_user_make_req = csc.requestThroughSig(cloudstack_admin_secretKey, cloudstack_account_make_req_body)
        cloudstacK_user_make_res = json.loads(cloudstacK_user_make_req)
        print("클라우드스택 유저 생성 response: ", cloudstacK_user_make_res)
        cloudstack_created_account_id = cloudstacK_user_make_res["createaccountresponse"]["account"]["id"]
        cloudstack_created_user_id = cloudstacK_user_make_res["createaccountresponse"]["account"]["user"][0]["id"]

        userKey_register_body = {     # 생성된 account의 cloudstack_user_apiKey, cloudstack_user_secretKey 등록
            "apiKey" : cloudstack_admin_apiKey,
            "response" : "json",
            "command" : "registerUserKeys",
            "id" : cloudstack_created_user_id
        }
        user_network_create_req = csc.requestThroughSig(cloudstack_admin_secretKey, userKey_register_body)
        user_network_create_res = json.loads(user_network_create_req)
        user_apiKey = user_network_create_res["registeruserkeysresponse"]["userkeys"]["apikey"]
        user_secretKey = user_network_create_res["registeruserkeysresponse"]["userkeys"]["secretkey"]

        try:
            print("유저의 vlan 할당")
            vlan_max = AccountInfo.objects.aggregate(Max("cloudstack_network_vlan"))
            print("현재 가장 큰 vlan 값: ", vlan_max)
            vlan = vlan_max["cloudstack_network_vlan__max"] + 1
            print("vlan 값: ", vlan)
        except Exception as e:
            print("에러 내용: ", e)
            vlan = 100
            print("생성된 유저가 없어 vlan값이 " + str(vlan) + "으로 할당됩니다.")

        user_network_create_body = {
            "apiKey" : user_apiKey,
            "response" : "json", 
            "command" : "createNetwork",
            "account" : input_data["user_id"],
            "domainid" : cloudstack_domainID,
            "vlan" : str(vlan),
            "displaytext" : input_data["user_id"] + "net",
            "name" : input_data["user_id"] + "net",
            "networkofferingid" : cloudstack_netOfferingID,
            "zoneid" : cloudstack_zoneID
        }
        user_network_create_req = csc.requestThroughSig(user_secretKey, user_network_create_body)
        user_network_create_res = json.loads(user_network_create_req)
        cloudstack_user_network_id = user_network_create_res["createnetworkresponse"]["network"]["id"]
        cloudstack_user_network_vlan = user_network_create_res["createnetworkresponse"]["network"]["vlan"]

        #장고 ORM 업데이트
        AccountInfo.objects.create(
            user_id = input_data['user_id'],
            email = input_data['email'],
            password = input_data['password'],
            openstack_user_id = openstack_created_user_id,
            openstack_user_project_id = openstack_user_project_id,
            cloudstack_account_id = cloudstack_created_account_id,
            cloudstack_apiKey = user_apiKey,
            cloudstack_secretKey = user_secretKey,
            cloudstack_network_id = cloudstack_user_network_id,
            cloudstack_network_vlan = cloudstack_user_network_vlan
        )

        user_network_create_req = JsonResponse(input_data, status=200)
        user_network_create_req['Access-Control-Allow-Origin'] = '*'

        return user_network_create_req

    @swagger_auto_schema(tags=["User Info Get API"], responses={200:"Success"})
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

    @swagger_auto_schema(tags=["User Delete API"], request_body=UserDeleteSerializer, responses={200:"Success"})
    def delete(self, request):  #그냥 api로 db랑 오픈스택에 유저 쌓인 거 정리하기 쉬우려고 만들었음. 후에 탈퇴기능 이용하려면 구현 제대로 할 것.
        input_data = json.loads(request.body)
        #------openstack account delete------#
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
        del_account_id_cloudstack = account_data.cloudstack_account_id
        # print(del_user_id_cloudstack)
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

        openstack_project_del_req = requests.delete("http://" + openstack_hostIP + "/identity/v3/projects/" + del_project_id_openstack,
            headers={'X-Auth-Token': admin_token})     #오픈스택에 해당 프로젝트 삭제 request
        openstack_user_del_req = requests.delete("http://" + openstack_hostIP + "/identity/v3/users/" + del_user_id_openstack,
            headers={'X-Auth-Token': admin_token})     #오픈스택에 해당 유저 삭제 request
        print(openstack_user_del_req)

        #------cloudstack account delete------#
        cloudstack_account_del_body={     # cloudstack account 삭제 request body
            "apiKey" : cloudstack_admin_apiKey,
            "response" : "json",
            "command" : "deleteAccount",
            "id" : del_account_id_cloudstack
        }
        cloudstack_account_del_req = csc.requestThroughSig(cloudstack_admin_secretKey, cloudstack_account_del_body)
        cloudstack_account_del_res = json.loads(cloudstack_account_del_req)
        print(cloudstack_account_del_res)

        account_data.delete()   # DB에서 사용자 정보 삭제

        return JsonResponse({"message" : "회원탈퇴가 완료되었습니다."}, status=200)

class SignView(APIView):
    @swagger_auto_schema(tags=["User SignIn API"], request_body=UserSignInSerializer, responses={200:"Success", 400:"Bad Request", 401:"Not Allowed"})
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