import os   #여기서 부터
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))    #여기까지는 상위 디렉토리 모듈 import 하기 위한 코드

import openstack_controller as oc    #백엔드 루트 디렉토리에 openstack.py 생성했고, 그 안에 공통으로 사용될 함수, 변수들 넣을 것임. 아직은 클래스화 안 했음.
import cloudstack_controller as csc
from log_manager import UserLogManager
import json
import requests
from .models import AccountInfo, AccountLog
from django.db.models import Max
from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from rest_framework.views import APIView
from drf_yasg.utils       import swagger_auto_schema
from drf_yasg             import openapi
from .serializers import UserRegisterSerializer, UserSignInSerializer   # UserDeleteSerializer, UserInfoSeializer

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


openstack_user_token = openapi.Parameter(   # for django swagger
    "X-Auth-Token",
    openapi.IN_HEADER,
    description = "access_token",
    type = openapi.TYPE_STRING
)
cloudstack_user_apiKey = openapi.Parameter(   # for django swagger
    "apiKey",
    openapi.IN_HEADER,
    description = "user's cloudstack apiKey",
    type = openapi.TYPE_STRING
)
cloudstack_user_secretKey = openapi.Parameter(   # for django swagger
    "secretKey",
    openapi.IN_HEADER,
    description = "user's cloudstack secretKey",
    type = openapi.TYPE_STRING
)

# request django url = /account/
class AccountView(UserLogManager, APIView):
    @swagger_auto_schema(tags=["User API"], request_body=UserRegisterSerializer, responses={200:"Success", 404:"Not Found", 409:"Conflict"})
    def post(self, cloudstack_account_make_req_body):
        input_data = json.loads(cloudstack_account_make_req_body.body)
        if AccountInfo.objects.filter(user_id=input_data["user_id"]).exists():
            return JsonResponse({"message" : "이미 존재하는 ID입니다."}, status=409)
        #------openstack user create------#
        admin_token = oc.admin_token()
        if admin_token == None:
            return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 회원가입을 진행할 수 없습니다."}, status=404)

        # 사용자의 openstack 정보
        openstack_user_payload = {
            "user": {
                "name": input_data['user_id'],
                "password": str(input_data['password']),
                "email": input_data["email"],
                "default_project_id": oc.admin_project_id   # admin 프로젝트에 유저 생성
            }
        }
        openstack_user_make_req = requests.post("http://" + openstack_hostIP + "/identity/v3/users",    # openstack 사용자 생성
            headers={'X-Auth-Token': admin_token},
            data=json.dumps(openstack_user_payload))
        print(openstack_user_make_req.json())   # 유저 생성 response 출력
        openstack_created_user_id = openstack_user_make_req.json()["user"]["id"]    # openstack user uuid 확인
        print(openstack_created_user_id)
        openstack_user_role_assignment_req = requests.put(          # 사용자에게 프로젝트 admin 역할 부여
            "http://" + openstack_hostIP + "/identity/v3/projects/" + oc.admin_project_id + "/users/" + openstack_created_user_id + "/roles/" + openstack_admin_role_id,
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

        userKey_register_body = {     # 생성된 account의 user_apiKey, user_secretKey 등록
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
            user_id = input_data["user_id"],
            email = input_data["email"],
            password = input_data["password"],
            first_name = input_data["first_name"],
            last_name = input_data["last_name"],
            openstack_user_id = openstack_created_user_id,
            openstack_user_project_id = openstack_admin_project_id,
            cloudstack_account_id = cloudstack_created_account_id,
            cloudstack_apiKey = user_apiKey,
            cloudstack_secretKey = user_secretKey,
            cloudstack_network_id = cloudstack_user_network_id,
            cloudstack_network_vlan = cloudstack_user_network_vlan
        )
        super().userLogAdder(input_data["user_id"], input_data["user_id"], "Sign Up", "user")

        user_network_create_req = JsonResponse(input_data, status=200)
        user_network_create_req['Access-Control-Allow-Origin'] = '*'

        return user_network_create_req

    @swagger_auto_schema(tags=["User API"], manual_parameters=[openstack_user_token, cloudstack_user_apiKey, cloudstack_user_secretKey], responses={200:"Success"})
    def get(self, request):                                   # 리퀘스트 헤더 중에 apiKey, secretKey는 무조건 오니까 apiKey로 유저 정보 get
        try:
            user_token = request.headers["X-Auth-Token"]
        except Exception as e:
            print("오픈스택 서버 에러, 오픈스택 유저 토큰 없음. 에러 내용: ", e)
            pass
        user_apiKey = request.headers["apiKey"]
        user_secretKey = request.headers["secretKey"]
        
        user_info_object = AccountInfo.objects.get(cloudstack_apiKey=user_apiKey)
        user_id = user_info_object.user_id
        user_email = user_info_object.email
        user_first_name = user_info_object.first_name
        user_last_name = user_info_object.last_name
        
        return JsonResponse({"user_id" : user_id, "email" : user_email, "first_name" : user_first_name, "last_name" : user_last_name}, status=200)

    @swagger_auto_schema(tags=["User API"], manual_parameters=[openstack_user_token, cloudstack_user_apiKey, cloudstack_user_secretKey], responses={200:"Success", 404:"Not Found"})
    def delete(self, request):  #그냥 api로 db랑 오픈스택에 유저 쌓인 거 정리하기 쉬우려고 만들었음. 후에 탈퇴기능 이용하려면 구현 제대로 할 것.
        try:
            user_token = request.header["X-Auth-Token"]
        except Exception as e:
            print("오픈스택 서버 에러, 오픈스택 유저 토큰 없음. 에러 내용: ", e)
            pass
        user_apiKey = request.headers["apiKey"]
        user_secretKey = request.headers["secretKey"]
        #------openstack account delete------#
        admin_token = oc.admin_token()
        if admin_token == None:
            return JsonResponse({"message" : "오픈스택 관리자 토큰을 받아올 수 없습니다."}, status=404)
        
        # del_user_id = AccountInfo.objects.get(input_data["user_id"]
        account_data_object = AccountInfo.objects.get(cloudstack_apiKey=user_apiKey)  #db에서 삭제할 유저 정보
        # print(account_data)
        del_project_id_openstack = account_data_object.openstack_user_project_id
        del_user_id_openstack = account_data_object.openstack_user_id  #해당 유저의 openstack user id
        # print(del_project_id_openstack)
        # print(del_user_id_openstack)
        del_account_id_cloudstack = account_data_object.cloudstack_account_id
        # print(del_user_id_cloudstack)
        user_openstack_resources = account_data_object.user_resource_info.all()   #해당 유저의 stack 정보(from 외래키 related name)
        user_cloudstack_resources = account_data_object.user_cloudstack_resource_info.all()

        for openstack_resource in user_openstack_resources:  # 오픈스택에서 user의 stack 모두 삭제
            if openstack_resource.stack_id != None:
                stack_del_req = requests.delete("http://" + openstack_hostIP + "/heat-api/v1/" + del_project_id_openstack + "/stacks/"
                    + openstack_resource.stack_name + "/" + openstack_resource.stack_id,
                    headers = {'X-Auth-Token' : admin_token})
                print("스택 삭제 리스폰스: ", stack_del_req)
            else:
                del_instance_id = openstack_resource.instance_id
                del_image_name = openstack_resource.image_name
                del_freezer_restored_instance_req = requests.delete("http://" + oc.hostIP + "/compute/v2.1/servers/" + del_instance_id,
                        headers={'X-Auth-Token': admin_token})
                print("프리저로 복원된 인스턴스 삭제 리스폰스: ", del_freezer_restored_instance_req)
                del_freezer_restore_image_id = requests.get("http://" + oc.hostIP + "/image/v2/images?name=" + del_image_name,
                    headers={'X-Auth-Token': admin_token}).json()["images"][0]["id"]
                del_freezer_restore_image_req = requests.delete("http://" + oc.hostIP + "/image/v2/images/" + del_freezer_restore_image_id,
                    headers={'X-Auth-Token': admin_token})
                print("프리저로 복원된 인스턴스의 이미지 삭제 리스폰스: ", del_freezer_restore_image_req)
            if openstack_resource.update_image_ID != None:
                image_del_req = requests.delete("http://" + openstack_hostIP + "/image/v2/images/" + openstack_resource.update_image_ID,
                    headers = {'X-Auth-Token' : admin_token})
                print("업데이트에 쓰인 이미지 삭제 리스폰스: ", image_del_req)
        openstack_user_del_req = requests.delete("http://" + openstack_hostIP + "/identity/v3/users/" + del_user_id_openstack,
            headers={'X-Auth-Token': admin_token})     #오픈스택에 해당 유저 삭제 request
        print("오픈스택 유저 삭제 리스폰스: ", openstack_user_del_req)

        #------cloudstack account delete------#
        cloudstack_account_del_body={     # cloudstack account 삭제 request body
            "apiKey" : cloudstack_admin_apiKey,
            "response" : "json",
            "command" : "deleteAccount",
            "id" : del_account_id_cloudstack
        }
        cloudstack_account_del_req = csc.requestThroughSig(cloudstack_admin_secretKey, cloudstack_account_del_body)
        cloudstack_account_del_res = json.loads(cloudstack_account_del_req)
        print("클라우드스택 유저 삭제 리스폰스: ", cloudstack_account_del_res)

        for cloudstack_resource in user_cloudstack_resources:
            del_cloudstack_template_id = cloudstack_resource.image_id
            cloudstack_template_del_req_body = {"apiKey" : csc.admin_apiKey, "response" : "json", "command" : "deleteTemplate", "id" : del_cloudstack_template_id}
            cloudstack_template_del_req = csc.requestThroughSig(csc.admin_secretKey, cloudstack_template_del_req_body)
            cloudstack_template_del_res = json.loads(cloudstack_template_del_req)
            print("유저가 클라우드스택에서 가지고 있던 template 삭제 결과: ", cloudstack_template_del_res)

        account_data_object.delete()   # DB에서 사용자 정보 삭제

        return JsonResponse({"message" : "회원탈퇴가 완료되었습니다."}, status=200)

# request django url = /account/login/
class SignView(UserLogManager, APIView):
    @swagger_auto_schema(tags=["User SignIn API"], request_body=UserSignInSerializer, responses={200:"Success", 206:"Partial Content", 400:"Bad Request", 401:"Not Allowed"})
    def post(self, request):
        input_data = json.loads(request.body)
        # 사용자의 openstack 정보
        try:
            if AccountInfo.objects.filter(user_id=input_data['user_id']).exists():
                user = AccountInfo.objects.get(user_id=input_data['user_id'])
                apiKey = AccountInfo.objects.get(user_id=input_data['user_id']).cloudstack_apiKey
                secretKey = AccountInfo.objects.get(user_id=input_data['user_id']).cloudstack_secretKey
                if user.password == input_data['password']:
                    openstack_user_token = oc.user_token(input_data)
                    if openstack_user_token == None:
                        super().userLogAdder(input_data["user_id"], input_data["user_id"], "Sign In", "user")
                        return JsonResponse({"apiKey" : apiKey, "secretKey" : secretKey}, status=206)
                    #hash token 해줄 것
                    super().userLogAdder(input_data["user_id"], input_data["user_id"], "Sign In", "user")
                    response = JsonResponse({"openstack_user_token" : openstack_user_token, "apiKey" : apiKey, "secretKey" : secretKey}, status=200)
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

# request django url = /account/log/<str:user_id>/
class LogView(APIView):
    user_id = openapi.Parameter('user_id', openapi.IN_PATH, description='User ID to get log', required=True, type=openapi.TYPE_STRING)

    @swagger_auto_schema(tags=["User Log API"], manual_parameters=[user_id], responses={200:"Success"})
    def get(self, request, user_id):
        log_list = list(AccountLog.objects.filter(user_id=user_id).values())
        log_list.reverse()

        return JsonResponse({"log" : log_list}, status=200)