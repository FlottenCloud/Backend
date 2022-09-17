import os      #여기서 부터
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))    #여기까지는 상위 디렉토리 모듈 import 하기 위한 코드

import openstack_controller as oc    #백엔드 루트 디렉토리에 openstack.py 생성했고, 그 안에 공통으로 사용될 함수, 변수들 넣을 것임.
import cloudstack_controller as csc
from .openstack_modules import *
import json
import requests
from sqlite3 import OperationalError
from .models import OpenstackInstance
from cloudstack.models import CloudstackInstance
import account.models
from django.db.models import Sum
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils       import swagger_auto_schema
from drf_yasg             import openapi
from openstack.serializers import CreateStackSerializer, UpdateStackSerializer, InstancePKSerializer, OpenstackInstanceSerializer
from django.http import JsonResponse
import time
# Create your views here.
openstack_hostIP = oc.hostIP
openstack_user_token = openapi.Parameter(   # for django swagger
    "X-Auth-Token",
    openapi.IN_HEADER,
    description = "access_token",
    type = openapi.TYPE_STRING
)

# request django url = /openstack/      인스턴스 CRUD 로직
class Openstack(Stack, APIView):
    @swagger_auto_schema(tags=["Openstack API"], manual_parameters=[openstack_user_token], request_body=CreateStackSerializer, responses={200:"Success", 401:"Unauthorized", 404:"Not Found", 405:"Method Not Allowed", 409:"Confilct"})
    def post(self, request):   # header: user_token, body: 요구사항({os, package[], num_people, data_size, instance_name, backup_time})
        stack_template_root = "templates/"
        try:
            input_data, token, user_id = oc.getRequestParamsWithBody(request)
            if user_id == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겼습니다."}, status=404)

            user_os, user_package, num_people, data_size, flavor, user_instance_name, backup_time = super().getUserRequirement(input_data)
            if user_instance_name == "Duplicated":
                return JsonResponse({"message": "이미 존재하는 가상머신 이름입니다."}, status=409)
            if flavor == "EXCEEDED":
                return JsonResponse({"message" : "인원 수 X 인원 당 예상 용량 값은 10G를 넘지 못합니다."}, status=405)

            openstack_tenant_id = account.models.AccountInfo.objects.get(user_id=user_id).openstack_user_project_id
            print("유저 프로젝트 id: ", openstack_tenant_id)

            if user_os == "ubuntu":
                with open(stack_template_root + 'ubuntu_1804.json','r') as f:   # 오픈스택에 ubuntu 이미지 안올려놨음
                    json_template_skeleton = json.load(f)
                    json_template = super().templateModify(json_template_skeleton, user_id, user_instance_name, flavor, user_package)
            elif user_os == "centos":
                with open(stack_template_root + 'cirros.json','r') as f:    # 오픈스택에 centos 이미지 안올려놔서 일단 cirros.json으로
                    json_template_skeleton = json.load(f)
                    json_template = super().templateModify(json_template_skeleton, user_id, user_instance_name, flavor, user_package)
            elif user_os == "fedora":
                with open(stack_template_root + 'fedora.json','r') as f:    #이걸로 생성 test
                    json_template_skeleton = json.load(f)
                    json_template = super().templateModify(json_template_skeleton, user_id, user_instance_name, flavor, user_package)
            
            #address heat-api v1 프로젝트 id stacks
            stack_req = super().reqCheckerWithData("post", "http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks",
                token, json_template)
            if stack_req == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 스택 정보를 가져올 수 없습니다."}, status=404)
            print("stack생성", stack_req.json())
            stack_id = stack_req.json()["stack"]["id"]

            stack_name_req = super().reqChecker("get", "http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks?id=" + stack_id,
                token)
            if stack_name_req == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 스택 이름을 가져올 수 없습니다."}, status=404)
            print("스택 이름 정보: ", stack_name_req.json())
            stack_name = stack_name_req.json()["stacks"][0]["stack_name"]

            try:
                instance_id, instance_name, instance_ip_address, instance_status, instance_image_name, instance_flavor_name, instance_ram_size, instance_disk_size, instance_num_cpu = super().stackResourceGetter("create", openstack_hostIP, openstack_tenant_id, user_id, stack_name, stack_id, token)
            except Exception as e:  # stackResourceGetter에서 None이 반환 된 경우
                print("예외 발생: ", e)
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 생성된 스택의 정보를 불러올 수 없습니다."}, status=404)
            
            package_for_db = ""     # db에 패키지 목록 문자화해서 저장하는 로직
            for i in range(len(user_package)):
                package_for_db += user_package[i]
                if i != len(user_package)-1:
                    package_for_db += ","
            # db에 저장 할 인스턴스 정보
            instance_data = {
                "user_id" : user_id,
                "stack_id" : stack_id,
                "stack_name" : stack_name,
                "instance_id" : instance_id,
                "instance_name" : instance_name,
                "ip_address" : str(instance_ip_address),
                "status" : instance_status,
                "image_name" : instance_image_name,
                "flavor_name" : instance_flavor_name,
                "ram_size" : instance_ram_size,
                "num_people" : num_people,
                "expected_data_size" : data_size,
                "disk_size" : instance_disk_size,
                "num_cpu" : instance_num_cpu,
                "package" : package_for_db,
                "backup_time" : backup_time,
                "os" : user_os
            }
            #serializing을 통한 인스턴스 정보 db 저장
            serializer = OpenstackInstanceSerializer(data=instance_data)
            if serializer.is_valid():
                serializer.save()
                print("saved")
                print(serializer.data)
            else:
                print("not saved")
                print(serializer.errors)
        
        except oc.TokenExpiredError as e:
            print("Token Expired: ", e)
            return JsonResponse({"message" : str(e)}, status=401)

        return JsonResponse({"message" : "가상머신 생성 완료"}, status=201)

    @swagger_auto_schema(tags=["Openstack API"], manual_parameters=[openstack_user_token], responses={200:"Success", 401:"Unauthorized", 404:"Not Found"})
    def get(self, request):     # header: user_token
        try:
            token, user_id = oc.getRequestParams(request)
            if user_id == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 token으로 오픈스택 유저의 정보를 얻어올 수 없습니다."}, status=404)

            try:
                user_instance_info = OpenstackInstance.objects.filter(user_id=user_id)
                for instance_info in user_instance_info:
                    # while(True):
                    #     instance_req = requests.get("http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_info.instance_id,
                    #     headers = {'X-Auth-Token' : token})
                    #     instance_status = instance_req.json()["server"]["status"]
                    #     if instance_status == OpenstackInstance.objects.filter(instance_id=instance_info.instance_id).status:
                    #         break
                    instance_req = super().reqChecker("get", "http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_info.instance_id, token)
                    if instance_req == None:
                        return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 인스턴스의 상태 정보를 가져올 수 없습니다."}, status=404)
                    instance_status = instance_req.json()["server"]["status"]
                    OpenstackInstance.objects.filter(instance_id=instance_info.instance_id).update(status=instance_status)

                user_stack_data = list(OpenstackInstance.objects.filter(user_id=user_id).values())
            except OperationalError:
                return JsonResponse({[]}, status=200)
        

        except oc.TokenExpiredError as e:
            print("에러 내용: ", e)
            return JsonResponse({"message" : str(e)}, status=401)

        return JsonResponse({"instances" : user_stack_data}, status=200)
    
    @swagger_auto_schema(tags=["Openstack API"], manual_parameters=[openstack_user_token], request_body=UpdateStackSerializer, responses={200:"Success", 401:"Unauthorized", 404:"Not Found", 405:"Method Not Allowed"})
    def patch(self, request):       # header: user_token, body: instance_id->instance_pk, 요구사항({package[], num_people, data_size, backup_time})
        try:
            input_data, token, user_id = oc.getRequestParamsWithBody(request)
            if user_id == None:
                raise OpenstackServerError
            
            stack_data = OpenstackInstance.objects.get(instance_pk=input_data["instance_pk"])
            # update_openstack_tenant_id = account.models.AccountInfo.objects.get(user_id=user_id).openstack_user_project_id
            # instance_id = stack_data.instance_id
            # update_stack_id = stack_data.stack_id
            # update_stack_name = stack_data.stack_name
            # flavor_before_update = stack_data.flavor_name   # 요구사항 변경에 따른 플레이버가 변경되는지 체크용
            # image_used_for_update = stack_data.update_image_ID

            # user_req_package, updated_num_people, updated_data_size, user_req_flavor, user_req_backup_time = super().getUserUpdateRequirement(input_data)
            # if user_req_flavor == "EXCEEDED":   # 용량이 10GB를 넘어간 경우
            #     return JsonResponse({"message" : "인원 수 X 인원 당 예상 용량 값은 10G를 넘지 못합니다."}, status=405)
            # elif user_req_flavor == flavor_before_update:   # 원래 쓰려던 용량과 같은 범위 내의 용량을 요구사항으로 입력했을 경우
            #     user_req_flavor = "NOTUPDATE"
            # else:
            #     if flavor_before_update == "ds1G" and user_req_flavor == "ds512M":  # 원래 쓰려던 용량보다 작은 용량을 요구사항으로 입력했을 경우
            #         user_req_flavor = "NOTUPDATE"

            # if user_req_backup_time != 6 and user_req_backup_time != 12:
            #     return JsonResponse({"message" : "백업 주기는 6시간, 12시간 중에서만 선택할 수 있습니다."}, status=405)
            
            # print("요청 정보: ", user_req_package, user_req_flavor, user_req_backup_time)

            # stack_environment_req = super().reqChecker("get", "http://" + openstack_hostIP + "/heat-api/v1/" + update_openstack_tenant_id + "/stacks/" 
            #     + update_stack_name + "/" + update_stack_id + "/environment", token)
            # if stack_environment_req == None:
            #     return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 인스턴스(스택)을 삭제할 수 없습니다."}, status=404)
            # print("기존 스택의 템플릿: ", stack_environment_req.json())

            # before_update_template_package = stack_environment_req.json()["parameters"]["packages"]
            # print("기존 스택의 템플릿 패키지: ", before_update_template_package)
            # # duplicated_package = list(set(before_update_template_package).intersection(user_req_package))
            # # print("중복된 패키지: ", duplicated_package)
            # # for package in duplicated_package :
            # #     user_req_package.remove(package)
            # # print("요청 패키지에서 기존의 패키지를 뺀 패키지: ", user_req_package)
            # package_origin_plus_user_req = before_update_template_package + user_req_package    # 기존 패키지 + 유저의 요청 패키지
            # package_for_db = ""     # db에 저장할 패키지 목록 문자화
            # for i in range(len(package_origin_plus_user_req)):
            #     package_for_db += package_origin_plus_user_req[i]
            #     if i != len(package_origin_plus_user_req)-1:
            #         package_for_db += ","

            # openstack_img_payload = { # 인스턴스의 스냅샷 이미지 만들기위한 payload
            #     "createImage": {
            #         "name": "backup_for_update_" + instance_id
            #     }
            # }
            # snapshot_req = super().reqCheckerWithData("post", "http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_id + "/action", 
            #     token, json.dumps(openstack_img_payload))
            # if snapshot_req == None:
            #     return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 프로세스를 진행할 수 없습니다."}, status=404)
            # print("인스턴스로부터 이미지 생성 리스폰스: ", snapshot_req)
            # snapshotID_for_update = snapshot_req.headers["Location"].split("/")[6]
            # print("image_ID : " + snapshotID_for_update)

            # while(True):
            #     image_status_req = super().reqChecker("get", "http://" + openstack_hostIP + "/image/v2/images/" + snapshotID_for_update, token)
            #     if image_status_req == None:
            #         return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 이미지 정보를 조회할 수 없습니다."}, status=404)
            #     print("이미지 상태 조회 리스폰스: ", image_status_req.json())

            #     image_status = image_status_req.json()["status"]
            #     if image_status == "active":
            #         break
            #     time.sleep(2)

            # update_template = {   # 이미지와 요구사항을 반영한 템플릿 생성
            #     "parameters": {
            #         "image": "backup_for_update_" + instance_id
            #     }
            # }
            # if len(user_req_package) != 0:
            #     update_template["parameters"]["packages"] = user_req_package
            # if user_req_flavor != "NOTUPDATE":
            #     update_template["parameters"]["flavor"] = user_req_flavor
            # print("업데이트용 Template : ", json.dumps(update_template))

            # stack_update_req = super().reqCheckerWithData("patch", "http://" + openstack_hostIP + "/heat-api/v1/" + update_openstack_tenant_id + "/stacks/" + update_stack_name + "/" + update_stack_id,
            #     token, json.dumps(update_template))
            # if stack_update_req == None:
            #     return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 인스턴스(스택)를 업데이트 할 수 없습니다."}, status=404)
            # print("stack 업데이트 결과: ", stack_update_req)
            # print("stack 업데이트 결과 헤더: ", stack_update_req.headers)

            # if image_used_for_update != None:
            #     image_used_for_update_del_req = super().reqChecker("delete", "http://" + openstack_hostIP + "/image/v2/images/" + image_used_for_update, token)
            #     if image_used_for_update_del_req == None:
            #         return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 이미지를 삭제할 수 없습니다."}, status=404)
            #     print("업데이트용 이미지의 이전 버전 삭제 요청 결과: ", image_used_for_update_del_req)

            # try:
            #     updated_instance_id, updated_instance_name, updated_instance_ip_address, updated_instance_status, updated_instance_image_name, updated_instance_flavor_name, updated_instance_ram_size, updated_disk_size, updated_num_cpu = super().stackResourceGetter("update", openstack_hostIP, update_openstack_tenant_id, user_id, update_stack_name, update_stack_id, token)
            # except Exception as e:  # stackResourceGetter에서 None이 반환 된 경우
            #     print("스택 정보 불러오는 중 예외 발생: ", e)
            #     return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 업데이트 된 스택의 정보를 불러올 수 없습니다."}, status=404)

            # Freezer로 복원 된 인스턴스가 아닌 경우    -> Stack.stackUpdater()
            if stack_data.stack_id != None:
                updated_instance_id, updated_instance_name, updated_instance_ip_address, updated_instance_status, updated_instance_image_name, updated_instance_flavor_name, updated_instance_ram_size, updated_disk_size, updated_num_cpu, package_for_db, updated_num_people,  updated_data_size, user_req_backup_time, snapshotID_for_update = super().stackUpdater(openstack_hostIP, input_data, token, user_id)
            # Freezer로 복원 된 인스턴스인 경우    -> Stack.stackUpdaterWhenFreezerRestored()
            else:
                updated_instance_id, updated_instance_name, updated_instance_ip_address, updated_instance_status, updated_instance_image_name, updated_instance_flavor_name, updated_instance_ram_size, updated_disk_size, updated_num_cpu, package_for_db, updated_num_people,  updated_data_size, user_req_backup_time, snapshotID_for_update = super().stackUpdaterWhenFreezerRestored(openstack_hostIP, input_data, token, user_id)

            OpenstackInstance.objects.filter(instance_pk=input_data["instance_pk"]).update(instance_id=updated_instance_id, instance_name=updated_instance_name,
                ip_address=str(updated_instance_ip_address), status=updated_instance_status, image_name=updated_instance_image_name, flavor_name=updated_instance_flavor_name,
                ram_size=updated_instance_ram_size, num_people=updated_num_people, expected_data_size=updated_data_size, disk_size=updated_disk_size, num_cpu=updated_num_cpu, 
                package=package_for_db, backup_time=user_req_backup_time, update_image_ID=snapshotID_for_update)

        except oc.TokenExpiredError as e:
            print("Token Expired: ", e)
            return JsonResponse({"message" : str(e)}, status=401)
        except oc.OpenstackServerError as e:
            print("스택 업데이트 중 예외 발생: ", e)
            return JsonResponse({"message" : "오픈스택 서버에 문제가 발생했습니다."}, status=404)
        except oc.OverSizeError as e:
            print("스택 업데이트 중 예외 발생: ", e)
            return JsonResponse({"message" : "인원 수 X 인원 당 예상 용량 값은 10G를 넘지 못합니다."}, status=405)

        return JsonResponse({"message" : "업데이트 완료"}, status=201)

    @swagger_auto_schema(tags=["Openstack API"], manual_parameters=[openstack_user_token], request_body=InstancePKSerializer, responses={200:"Success", 404:"Not Found"})
    def delete(self, request):      # header: user_token, body: instance_pk
        try:
            input_data, token, user_id = oc.getRequestParamsWithBody(request)
            if user_id == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 token으로 오픈스택 유저의 정보를 얻어올 수 없습니다."}, status=404)
            
            #------------Openstack Stack and Image Delete------------#
            openstack_stack_data = OpenstackInstance.objects.get(instance_pk=input_data["instance_pk"])
            del_instance_name = openstack_stack_data.instance_name
            del_stack_id = openstack_stack_data.stack_id
            del_stack_name = openstack_stack_data.stack_name
            del_update_image_id = openstack_stack_data.update_image_ID
            print("삭제한 가상머신 이름: " + del_instance_name + "\n삭제한 스택 이름: " + del_stack_name + "\n삭제한 스택 ID: " + del_stack_id)

            del_openstack_tenant_id = account.models.AccountInfo.objects.get(user_id=user_id).openstack_user_project_id
            stack_del_req = super().reqChecker("delete", "http://" + openstack_hostIP + "/heat-api/v1/" + del_openstack_tenant_id + "/stacks/"
                + del_stack_name + "/" + del_stack_id, token)
            if stack_del_req == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 인스턴스(스택)을 삭제할 수 없습니다."}, status=404)
            
            if del_update_image_id != None: # 업데이트를 한 번이라도 했을 시 업데이트에 쓰인 이미지도 삭제
                update_image_del_req = super().reqChecker("delete", "http://" + openstack_hostIP + "/image/v2/images/" + del_update_image_id, token)
                print("업데이트에 쓰인 이미지 삭제 리스폰스: ", update_image_del_req)
                if update_image_del_req == None:
                    return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 업데이트 때 사용한 이미지를 삭제할 수 없습니다."}, status=404)
                
            if openstack_stack_data.instance_backup_img_file.filter(instance_pk=input_data["instance_pk"]).exists():
                del_backup_image_id = openstack_stack_data.instance_backup_img_file.get(instance_pk=input_data["instance_pk"])
                backup_img_del_req = super().reqChecker("delete", "http://" + openstack_hostIP + "/image/v2/images/" + del_backup_image_id, token)
                print("인스턴스의 백업 이미지 삭제 리스폰스: ", backup_img_del_req)
                if backup_img_del_req == None:
                    return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 업데이트 때 사용한 이미지를 삭제할 수 없습니다."}, status=404)
                
            openstack_stack_data.delete() # DB에서 해당 stack row 삭제
                
            #------------Cloudstack Instance and Image Delete------------#
            if CloudstackInstance.objects.filter(instance_name=del_instance_name).exists():     # 클라우드스택에 백업 인스턴스가 만들어져 있을 경우
                cloudstack_instance_data = CloudstackInstance.objects.get(instance_name=del_instance_name)  # 인스턴스 name으로 CloudstackInstance 테이블에서 object get
                del_cloudstack_instance_id = cloudstack_instance_data.instance_id
                del_cloudstack_instance_template_id = cloudstack_instance_data.image_id
                print("클라우드스택에서 삭제할 인스턴스의 id: ", del_cloudstack_instance_id, " 삭제할 인스턴스의 템플릿 id: ", del_cloudstack_instance_template_id)
                
                cloudstack_instance_del_req_body = {{"apiKey" : csc.admin_apiKey, "response" : "json", "command" : "expungeVirtualMachine", "id" : del_cloudstack_instance_id}}
                cloudstack_instance_del_req = csc.requestThroughSig(csc.admin_secretKey, cloudstack_instance_del_req_body)
                cloudstack_template_del_req_body = {{"apiKey" : csc.admin_apiKey, "response" : "json", "command" : "deleteTemplate", "id" : del_cloudstack_instance_template_id}}
                cloudstack_template_del_req = csc.requestThroughSig(csc.admin_secretKey, cloudstack_template_del_req_body)
                
                cloudstack_instance_data.delete()

        except oc.TokenExpiredError as e:
            print("에러 내용: ", e)
            return JsonResponse({"message" : str(e)}, status=401)

        return JsonResponse({"message" : "가상머신 " + del_instance_name + " 삭제 완료"}, status=200)


# request django url = /openstack/<int:instance_pk>/
class InstanceInfo(APIView):
    instance_pk = openapi.Parameter('instance_pk', openapi.IN_PATH, description='Instance ID to get info', required=True, type=openapi.TYPE_INTEGER)
    
    @swagger_auto_schema(ta0gs=["Openstack API"], manual_parameters=[openstack_user_token, instance_pk], responses={200:"Success", 404:"Not Found"})
    def get(self, request, instance_pk):
        token, user_id = oc.getRequestParams(request)
        if user_id == None:
            return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 인스턴스 정보를 불러올 수 없습니다."}, status=404)
        try:
            instance_object = OpenstackInstance.objects.get(instance_pk=instance_pk)
        except Exception as e:
            print("인스턴스 정보 조회 중 예외 발생: ", e)
            return JsonResponse({"message" : "해당 가상머신이 존재하지 않습니다."}, status=404)  
        
        object_own_user_id = user_id
        object_instance_pk = instance_object.instance_pk
        object_instance_id = instance_object.instance_id
        object_instance_name = instance_object.instance_name
        object_stack_id = instance_object.stack_id
        object_stack_name = instance_object.stack_name
        object_ip_address = instance_object.ip_address
        object_status = instance_object.status
        object_image_name = instance_object.image_name
        object_os = instance_object.os
        object_flavor_name= instance_object.flavor_name
        object_ram_size = instance_object.ram_size
        object_num_people = instance_object.num_people
        object_data_size = instance_object.expected_data_size
        object_disk_size = instance_object.disk_size
        object_num_cpu = instance_object.num_cpu
        object_package = instance_object.package #json.loads(instance_object.package)#json.decoder.JSONDecoder.decode(instance_object.package)
        object_backup_time = instance_object.backup_time
        object_update_image_id = instance_object.update_image_ID
        
        response = JsonResponse({"user_id" : object_own_user_id, "instance_pk" : object_instance_pk, "instance_id" : object_instance_id, "instance_name" : object_instance_name, "stack_id" : object_stack_id, "stack_name" : object_stack_name, 
            "ip_address" : object_ip_address, "status" : object_status, "image_name" : object_image_name, "os" : object_os, "flavor_name" : object_flavor_name, "ram_size" : object_ram_size,
            "num_people" : object_num_people, "expected_data_size" : object_data_size, "disk_size" : object_disk_size, "num_cpu" : object_num_cpu, "backup_time" : object_backup_time, "package" : object_package,
            "update_image" : object_update_image_id}, status=200)
        
        return response

# request django url = /openstack/dashboard/            대쉬보드에 리소스 사용량 보여주기 용
class DashBoard(RequestChecker, APIView):
    @swagger_auto_schema(tags=["Openstack Dashboard API"], manual_parameters=[openstack_user_token], responses={200:"Success", 404:"Not Found"})
    def get(self, request):     # header: user_token
        try:
            token, user_id = oc.getRequestParams(request)
            if user_id == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 token으로 오픈스택 유저의 정보를 얻어올 수 없습니다."}, status=404)

            try:
                user_instance_info = OpenstackInstance.objects.filter(user_id=user_id)
                for instance_info in user_instance_info:    # 대쉬보드 출력에 status는 굳이 필요없지만, db 정보 최신화를 위해 status 업데이트.
                    instance_status_req = super().reqChecker("get", "http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_info.instance_id, token)
                    if instance_status_req == None:
                        return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 리소스 정보를 받아올 수 없습니다."}, status=404)

                    instance_status = instance_status_req.json()["server"]["status"]
                    OpenstackInstance.objects.filter(instance_id=instance_info.instance_id).update(status=instance_status)

                num_instances = OpenstackInstance.objects.filter(user_id=user_id).count()
                total_ram_size = OpenstackInstance.objects.filter(user_id=user_id).aggregate(Sum("ram_size"))   # 여기서부터
                total_disk_size = OpenstackInstance.objects.filter(user_id=user_id).aggregate(Sum("disk_size"))
                total_num_cpu = OpenstackInstance.objects.filter(user_id=user_id).aggregate(Sum("num_cpu")) # 여기까지 다 dict형식
                
                dashboard_data = {
                    "num_instances" : num_instances,    # max = 10
                    "total_ram_size" : total_ram_size["ram_size__sum"], # max = 50G
                    "total_disk_size" : total_disk_size["disk_size__sum"],   # max = 1000G
                    "total_num_cpu" : total_num_cpu["num_cpu__sum"]
                }

            except OperationalError:
                return JsonResponse({[]}, status=200)
        

        except oc.TokenExpiredError as e:
            print("에러 내용: ", e)
            return JsonResponse({"message" : str(e)}, status=401)

        return JsonResponse(dashboard_data)



class InstanceStart(RequestChecker, Instance, APIView):
    @swagger_auto_schema(tags=["Openstack Instance API"], manual_parameters=[openstack_user_token], request_body=InstancePKSerializer, responses={202:"Accepted", 404:"Not Found"})
    def post(self, request):    # header: user_token, body: instance_pk
        try:
            input_data, token, user_id = oc.getRequestParamsWithBody(request)   # 요청에는 user_id를 안쓰지만, exception 처리를 위해 user_id None인지 체크용으로 받아옴.
            if user_id == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 token으로 오픈스택 유저의 정보를 얻어올 수 없습니다."}, status=404)
            
            start_instance_pk = super().checkDataBaseInstanceID(input_data)
            start_instance_id = OpenstackInstance.objects.get(instance_pk=start_instance_pk).instance_id
            if start_instance_pk == None :
                return JsonResponse({"message" : "인스턴스를 찾을 수 없습니다."}, status=404)
            elif OpenstackInstance.objects.get(instance_pk=start_instance_pk).status == "ERROR" :
                return JsonResponse({"message" : "인스턴스가 ERROR 상태입니다."}, status=400)

            server_start_payload = {
                "os-start" : None
            }
            instance_start_req = super().reqCheckerWithData("post", "http://"+openstack_hostIP + "/compute/v2.1/servers/" + start_instance_id
                + "/action", token, json.dumps(server_start_payload))
            if instance_start_req == None:    # "오픈스택과 통신이 안됐을 시(timeout 시)"
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 해당 동작을 수행할 수 없습니다."})

        except oc.TokenExpiredError as e:
            print("에러 내용: ", e)
            return JsonResponse({"message" : str(e)}, status=401)
        
        return JsonResponse({"message" : "가상머신 시작"}, status=202)


class InstanceStop(RequestChecker, Instance, APIView):
    @swagger_auto_schema(tags=["Openstack Instance API"], manual_parameters=[openstack_user_token], request_body=InstancePKSerializer, responses={202:"Accepted", 404:"Not Found"})
    def post(self, request):    # header: user_token, body: instance_pk
        try:
            input_data, token, user_id = oc.getRequestParamsWithBody(request)   # 요청에는 user_id를 안쓰지만, exception 처리를 위해 user_id None인지 체크용으로 받아옴.
            if user_id == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 token으로 오픈스택 유저의 정보를 얻어올 수 없습니다."}, status=404)

            stop_instance_pk = super().checkDataBaseInstanceID(input_data)
            stop_instance_id = OpenstackInstance.objects.get(instance_pk=stop_instance_pk).instance_id
            if stop_instance_id == None :
                return JsonResponse({"message" : "인스턴스를 찾을 수 없습니다."}, status=404)

            server_stop_payload = {
                "os-stop" : None
            }
            instance_stop_req = super().reqCheckerWithData("post", "http://"+openstack_hostIP + "/compute/v2.1/servers/" + stop_instance_id
                + "/action", token, json.dumps(server_stop_payload))
            if instance_stop_req == None:    # "오픈스택과 통신이 안됐을 시(timeout 시)"
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 해당 동작을 수행할 수 없습니다."})
        

        except oc.TokenExpiredError as e:
            print("에러 내용: ", e)
            return JsonResponse({"message" : str(e)}, status=401)
        
        return JsonResponse({"message" : "가상머신 전원 끔"}, status=202)


class InstanceConsole(RequestChecker, Instance, APIView):
    @swagger_auto_schema(tags=["Openstack Instance API"], manual_parameters=[openstack_user_token], request_body=InstancePKSerializer, responses={200:"Success", 404:"Not Found"})
    def post(self, request):    # header: user_token, body: instance_pk
        try:
            input_data, token, user_id = oc.getRequestParamsWithBody(request)   # 요청에는 user_id를 안쓰지만, exception 처리를 위해 user_id None인지 체크용으로 받아옴.
            if user_id == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 token으로 오픈스택 유저의 정보를 얻어올 수 없습니다."}, status=404)

            console_for_instance_pk = super().checkDataBaseInstanceID(input_data)
            console_for_instance_id = OpenstackInstance.objects.get(instance_pk=console_for_instance_pk).instance_id
            if console_for_instance_id == None :
                return JsonResponse({"message" : "인스턴스를 찾을 수 없습니다."}, status=404)
            
            instance_console_payload ={
                "os-getVNCConsole": {
                    "type": "novnc"
                }
            }
            instance_console_req = super().reqCheckerWithData("post", "http://" + openstack_hostIP + "/compute/v2.1/servers/" + console_for_instance_id
                + "/action", token, json.dumps(instance_console_payload))
            if instance_console_req == None:    # "오픈스택과 통신이 안됐을 시(timeout 시)"
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 해당 동작을 수행할 수 없습니다."})
        
            splitted_url = instance_console_req.json()["console"]["url"].split("/") # 인스턴스 콘솔 접속 IP를 가상머신 내부 네트워크 IP가 아닌 포트포워딩 해놨던 PC의 공인 IP로 바꾸기 위한 로직
            splitted_url[2] = oc.hostIP+":6080"
            instance_url = "/".join(splitted_url)
        

        except oc.TokenExpiredError as e:
            print("에러 내용: ", e)
            return JsonResponse({"message" : str(e)}, status=401)

        return JsonResponse({"instance_url" : instance_url}, status=200)