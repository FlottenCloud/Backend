import os      #여기서 부터
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))    #여기까지는 상위 디렉토리 모듈 import 하기 위한 코드

import openstack_controller as oc    #백엔드 루트 디렉토리에 openstack.py 생성했고, 그 안에 공통으로 사용될 함수, 변수들 넣을 것임.
import cloudstack_controller as csc
from log_manager import InstanceLogManager
from .openstack_modules import *
import json
import requests
from sqlite3 import OperationalError
from django.db.models import Q
from .models import OpenstackInstance, OpenstackBackupImage, InstanceLog, ServerStatusFlag, DjangoServerTime
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
class Openstack(InstanceLogManager, Stack, APIView):
    @swagger_auto_schema(tags=["Openstack API"], manual_parameters=[openstack_user_token], request_body=CreateStackSerializer, responses={200:"Success", 400:"Bad Request", 401:"Unauthorized", 404:"Not Found", 409:"Conflict", 500:"Internal Server Error"})
    def post(self, request):   # header: user_token, body: 요구사항({os, package[], num_people, data_size, instance_name, backup_time})
        stack_template_root = "templates/"
        try:
            input_data, token, user_id = oc.getRequestParamsWithBody(request)
            if user_id == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겼습니다."}, status=500)

            user_os, user_package, pc_spec, flavor, user_instance_name, backup_time = super().getUserRequirement(input_data)
            if user_instance_name == "Duplicated":
                return JsonResponse({"message": "이미 존재하는 가상머신 이름입니다."}, status=409)
            if flavor == "EXCEEDED":
                return JsonResponse({"message" : "인원 수 X 인원 당 예상 용량 값은 10G를 넘지 못합니다."}, status=400)

            openstack_tenant_id = account.models.AccountInfo.objects.get(user_id=user_id).openstack_user_project_id
            print("유저 프로젝트 id: ", openstack_tenant_id)

            if user_os == "ubuntu":
                with open(stack_template_root + 'ubuntu_1804.json','r') as f:   # 오픈스택에 ubuntu 이미지 안올려놨음
                    json_template_skeleton = json.load(f)
                    json_template = super().templateModify(json_template_skeleton, user_instance_name, flavor, user_package)
            elif user_os == "centos":
                with open(stack_template_root + 'cirros.json','r') as f:    # 오픈스택에 centos 이미지 안올려놔서 일단 cirros.json으로
                    json_template_skeleton = json.load(f)
                    json_template = super().templateModify(json_template_skeleton, user_instance_name, flavor, user_package)
            elif user_os == "fedora":
                with open(stack_template_root + 'fedora.json','r') as f:    #이걸로 생성 test
                    json_template_skeleton = json.load(f)
                    json_template = super().templateModify(json_template_skeleton, user_instance_name, flavor, user_package)
            
            #address heat-api v1 프로젝트 id stacks
            stack_req = super().reqCheckerWithData("post", "http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks",
                token, json_template)
            if stack_req == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 스택 정보를 가져올 수 없습니다."}, status=500)
            print("stack생성", stack_req.json())
            stack_id = stack_req.json()["stack"]["id"]

            stack_name_req = super().reqChecker("get", "http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks?id=" + stack_id,
                token)
            if stack_name_req == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 스택 이름을 가져올 수 없습니다."}, status=500)
            print("스택 이름 정보: ", stack_name_req.json())
            stack_name = stack_name_req.json()["stacks"][0]["stack_name"]

            try:
                instance_id, instance_name, instance_ip_address, instance_status, instance_image_name, instance_flavor_name, instance_ram_size, instance_disk_size, instance_num_cpu = super().stackResourceGetter("create", openstack_hostIP, openstack_tenant_id, stack_name, stack_id, token)
            except Exception as e:  # stackResourceGetter에서 None이 반환 된 경우
                print("예외 발생: ", e)
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 생성된 스택의 정보를 불러올 수 없습니다."}, status=500)
            
            package_for_db = (",").join(user_package)   # db에 패키지 목록 문자화해서 저장하는 로직
    
            instance_data = {   # db에 저장 할 인스턴스 정보
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
                "pc_spec" : pc_spec,
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

            instance_pk = OpenstackInstance.objects.get(instance_id=instance_id).instance_pk    # 로그 저장을 위해 인스턴스 생성된 인스턴스의 pk값 받아옴
            super().userLogAdder(user_id, instance_name, "Created", "instance")
            super().instanceLogAdder(instance_pk, instance_name, "create", "Created")
        
        except oc.TokenExpiredError as e:
            print("Token Expired: ", e)
            return JsonResponse({"message" : str(e)}, status=401)
        except oc.InstanceNameNoneError:
            print("인스턴스 이름이 입력되지 않았습니다.")
            return JsonResponse({"message" : "생성할 인스턴스의 이름을 입력해주세요."}, status=400)
        except oc.NumPeopleNegativeError:
            print("사람 수가 음수입니다.")
            return JsonResponse({"message" : "예상 인원은 양수를 입력해주세요."}, status=400)
        except oc.ExpectedDataSizeNegativeError:
            print("예상 데이터 사이즈가 음수입니다.")
            return JsonResponse({"message" : "예상 데이터 사이즈는 양수를 입력해주세요."}, status=400)

        return JsonResponse({"message" : "가상머신 생성 완료"}, status=201)

    @swagger_auto_schema(tags=["Openstack API"], manual_parameters=[openstack_user_token], responses={200:"Success", 401:"Unauthorized", 404:"Not Found", 500:"Internal Server Error"})
    def get(self, request):     # header: user_token
        try:
            if ServerStatusFlag.objects.get(platform_name="openstack").status == True:
                token, user_id = oc.getRequestParams(request)
            else:
                user_id = AccountInfo.objects.get(cloudstack_apiKey=request.headers["apiKey"]).user_id
            q = Q()     # Query를 통한 가상머신 검색을 위한 where 절
            query_instance_name = request.GET.get("instance_name", None)    # Query에 instance_name있는지 확인
            print("Instance name for search: ", query_instance_name)

            try:
                user_stack_data = list(OpenstackInstance.objects.filter(user_id=user_id).values())
                for stack_data in user_stack_data:
                    instance_pk = stack_data["instance_pk"]
                    stack_data = super().instance_backup_time_show(stack_data, instance_pk)
                print(user_stack_data)

                if query_instance_name:   # Query에 가상머신 이름이 있으면
                    q &= Q(instance_name=query_instance_name)   # where절을 통해 해당 가상머신만 추출
                    print("Searched instance is")
                    searched_instance = list(OpenstackInstance.objects.filter(q).values())
                    instance_pk = searched_instance[0]["instance_pk"]
                    print(searched_instance)
                    searched_instance[0] = super().instance_backup_time_show(searched_instance[0], instance_pk)

                    return JsonResponse({"instance" : searched_instance}, status=200)

            except OperationalError:
                return JsonResponse({[]}, status=200)
        
        except oc.TokenExpiredError as e:
            print("에러 내용: ", e)
            return JsonResponse({"message" : str(e)}, status=401)
        
        return JsonResponse({"instances" : user_stack_data}, status=200)
    
    @swagger_auto_schema(tags=["Openstack API"], manual_parameters=[openstack_user_token], request_body=UpdateStackSerializer, responses={200:"Success", 400:"Bad Request", 401:"Unauthorized", 404:"Not Found", 500:"Internal Server Error"})
    def patch(self, request):       # header: user_token, body: instance_id->instance_pk, 요구사항({package[], num_people, data_size, backup_time})
        try:
            input_data, token, user_id = oc.getRequestParamsWithBody(request)
            if user_id == None:
                raise OpenstackServerError
            
            stack_data = OpenstackInstance.objects.get(instance_pk=input_data["instance_pk"])

            if stack_data.stack_id != None:     # Freezer로 복원 된 인스턴스가 아닌 경우    -> Stack.stackUpdater()
                updated_instance_id, updated_instance_name, updated_instance_ip_address, updated_instance_status, updated_instance_image_name, updated_instance_flavor_name, updated_instance_ram_size, updated_disk_size, updated_num_cpu, package_for_db, updated_pc_spec, user_req_backup_time, snapshotID_for_update = super().stackUpdater(openstack_hostIP, input_data, token, user_id)
                OpenstackInstance.objects.filter(instance_pk=input_data["instance_pk"]).update(instance_id=updated_instance_id, instance_name=updated_instance_name,
                    ip_address=str(updated_instance_ip_address), status=updated_instance_status, image_name=updated_instance_image_name, flavor_name=updated_instance_flavor_name,
                    ram_size=updated_instance_ram_size, pc_spec=updated_pc_spec, disk_size=updated_disk_size, num_cpu=updated_num_cpu, 
                    package=package_for_db, backup_time=user_req_backup_time, update_image_ID=snapshotID_for_update)
            else:       # Freezer로 복원 된 인스턴스인 경우    -> Stack.stackUpdaterWhenFreezerRestored()
                updated_instance_id, updated_instance_name, updated_instance_ip_address, updated_instance_status, updated_instance_image_name, updated_instance_flavor_name, updated_instance_ram_size, updated_disk_size, updated_num_cpu, package_for_db, updated_pc_spec, user_req_backup_time, snapshotID_for_update, updated_stack_name, updated_stack_id = super().stackUpdaterWhenFreezerRestored(openstack_hostIP, input_data, token, user_id)
                OpenstackInstance.objects.filter(instance_pk=input_data["instance_pk"]).update(instance_id=updated_instance_id, instance_name=updated_instance_name, stack_id=updated_stack_id,
                    stack_name=updated_stack_name, ip_address=str(updated_instance_ip_address), status=updated_instance_status, image_name=updated_instance_image_name,
                    flavor_name=updated_instance_flavor_name, ram_size=updated_instance_ram_size, pc_spec=updated_pc_spec, disk_size=updated_disk_size,
                    num_cpu=updated_num_cpu, package=package_for_db, backup_time=user_req_backup_time, update_image_ID=snapshotID_for_update)

            super().userLogAdder(user_id, updated_instance_name, "Updated", "instance")
            super().instanceLogAdder(input_data["instance_pk"], updated_instance_name, "update", "Updated")

        except oc.TokenExpiredError as e:
            print("Token Expired: ", e)
            return JsonResponse({"message" : str(e)}, status=401)
        except oc.OpenstackServerError as e:
            print("스택 업데이트 중 예외 발생: ", e)
            return JsonResponse({"message" : "오픈스택 서버에 문제가 발생했습니다."}, status=500)
        except oc.NumPeopleNegativeError:
            print("사람 수가 음수입니다.")
            return JsonResponse({"message" : "예상 인원은 양수를 입력해주세요."}, status=400)
        except oc.ExpectedDataSizeNegativeError:
            print("예상 데이터 사이즈가 음수입니다.")
            return JsonResponse({"message" : "예상 데이터 사이즈는 양수를 입력해주세요."}, status=400)
        except oc.OverSizeError as e:
            print("스택 업데이트 중 예외 발생: ", e)
            return JsonResponse({"message" : "인원 수 X 인원 당 예상 용량 값은 10G를 넘지 못합니다."}, status=400)
        except oc.StackUpdateFailedError as e:
            print("스택 업데이트 중 예외 발생: ", e)
            return JsonResponse({"message" : "스택 업데이트에 실패했습니다."}, status=500)
        except oc.InstanceImageUploadingError as e:
            print("스택 업데이트 중 예외 발생: ", e)
            return JsonResponse({"message" : "인스턴스가 현재 이미지 업로딩 상태입니다. 잠시 후 시도해주세요."}, status=500)
        except oc.ImageFullError as e:
            print("스택 업데이트 중 예외 발생: ", e)
            return JsonResponse({"message" : "오픈스택의 Image 용량이 가득 찼습니다."}, status=500)

        return JsonResponse({"message" : "업데이트 완료"}, status=201)

    @swagger_auto_schema(tags=["Openstack API"], manual_parameters=[openstack_user_token], request_body=InstancePKSerializer, responses={200:"Success", 404:"Not Found", 500:"Internal Server Error"})
    def delete(self, request):      # header: user_token, body: instance_pk
        try:
            admin_token = oc.admin_token()
            input_data, user_token, user_id = oc.getRequestParamsWithBody(request)
            if user_id == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 token으로 오픈스택 유저의 정보를 얻어올 수 없습니다."}, status=500)
            
            #------------Openstack Stack and Image Delete------------#
            openstack_stack_data = OpenstackInstance.objects.get(instance_pk=input_data["instance_pk"])
            del_instance_name = openstack_stack_data.instance_name
            del_instance_id = openstack_stack_data.instance_id
            del_stack_id = openstack_stack_data.stack_id
            del_stack_name = openstack_stack_data.stack_name
            del_image_name = openstack_stack_data.image_name
            del_update_image_id = openstack_stack_data.update_image_ID
            print("삭제한 가상머신 이름: " + del_instance_name + "\n삭제한 스택 이름: " + del_stack_name + "\n삭제한 스택 ID: " + del_stack_id)

            del_openstack_tenant_id = account.models.AccountInfo.objects.get(user_id=user_id).openstack_user_project_id
            try:
                if del_stack_id != None:
                    stack_del_req = requests.delete("http://" + openstack_hostIP + "/heat-api/v1/" + del_openstack_tenant_id + "/stacks/" + del_stack_name + "/" + del_stack_id, 
                        headers={'X-Auth-Token' : admin_token})
                else:   # In case instance is restored through freezer
                    del_freezer_restored_instance_req = requests.delete("http://" + oc.hostIP + "/compute/v2.1/servers/" + del_instance_id,
                        headers={'X-Auth-Token': admin_token})
                    del_freezer_restore_image_id = requests.get("http://" + oc.hostIP + "/image/v2/images?name=" + del_image_name,
                        headers={'X-Auth-Token': admin_token}).json()["images"][0]["id"]
                    del_freezer_restore_image_req = requests.delete("http://" + oc.hostIP + "/image/v2/images/" + del_freezer_restore_image_id,
                        headers={'X-Auth-Token': admin_token})
                    print("Deleted freezer backuped instance", del_freezer_restored_instance_req.status_code, del_freezer_restore_image_req.status_code)    
            except Exception as e:
                print("Error occurred while deleting stack, error message: ", e, " Stack delete response at openstack: ", stack_del_req.status_code)
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 인스턴스(스택)을 삭제할 수 없습니다."}, status=500)
            
            if del_update_image_id != None: # 업데이트를 한 번이라도 했을 시 업데이트에 쓰인 이미지도 삭제
                update_image_del_req = super().reqChecker("delete", "http://" + openstack_hostIP + "/image/v2/images/" + del_update_image_id, user_token)
                print("업데이트에 쓰인 이미지 삭제 리스폰스: ", update_image_del_req)
                if update_image_del_req == None:
                    return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 업데이트 때 사용한 이미지를 삭제할 수 없습니다."}, status=500)
                
            openstack_stack_data.delete() # DB에서 해당 stack row 삭제
                
            #------------Cloudstack Instance and Image Delete------------#
            if CloudstackInstance.objects.filter(instance_name=del_instance_name).exists():     # 클라우드스택에 백업 인스턴스가 만들어져 있을 경우
                cloudstack_instance_data = CloudstackInstance.objects.get(instance_name=del_instance_name)  # 인스턴스 name으로 CloudstackInstance 테이블에서 object get
                del_cloudstack_instance_id = cloudstack_instance_data.instance_id
                del_cloudstack_instance_template_id = cloudstack_instance_data.image_id
                print("클라우드스택에서 삭제할 인스턴스의 id: ", del_cloudstack_instance_id, " 삭제할 인스턴스의 템플릿 id: ", del_cloudstack_instance_template_id)
                
                cloudstack_instance_del_req_body = {"apiKey" : csc.admin_apiKey, "response" : "json", "command" : "destroyVirtualMachine", "id" : del_cloudstack_instance_id, "expunge": "true"}
                cloudstack_instance_del_req = csc.requestThroughSig(csc.admin_secretKey, cloudstack_instance_del_req_body)
                cloudstack_template_del_req_body = {"apiKey" : csc.admin_apiKey, "response" : "json", "command" : "deleteTemplate", "id" : del_cloudstack_instance_template_id}
                cloudstack_template_del_req = csc.requestThroughSig(csc.admin_secretKey, cloudstack_template_del_req_body)
                
                cloudstack_instance_data.delete()

            super().userLogAdder(user_id, del_instance_name, "Deleted", "instance")

        except oc.TokenExpiredError as e:
            print("에러 내용: ", e)
            return JsonResponse({"message" : str(e)}, status=401)

        return JsonResponse({"message" : "가상머신 " + del_instance_name + " 삭제 완료"}, status=200)

# request django url = /openstack/<int:instance_pk>/
class InstanceInfo(Instance, APIView):
    instance_pk = openapi.Parameter('instance_pk', openapi.IN_PATH, description='Instance ID to get info', required=True, type=openapi.TYPE_INTEGER)
    
    @swagger_auto_schema(tags=["Openstack Instance Info API"], manual_parameters=[openstack_user_token, instance_pk], responses={200:"Success", 404:"Not Found", 500:"Internal Server Error"})
    def get(self, request, instance_pk):
        if ServerStatusFlag.objects.get(platform_name="openstack").status == True:
            token, user_id = oc.getRequestParams(request)
        else:
            user_id = AccountInfo.objects.get(cloudstack_apiKey=request.headers["apiKey"]).user_id
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
        object_pc_spec = instance_object.pc_spec
        object_disk_size = instance_object.disk_size
        object_num_cpu = instance_object.num_cpu
        object_package = instance_object.package
        object_backup_time = instance_object.backup_time
        object_update_image_id = instance_object.update_image_ID
        instance_info = {"user_id" : object_own_user_id, "instance_pk" : object_instance_pk, "instance_id" : object_instance_id, "instance_name" : object_instance_name, "stack_id" : object_stack_id, "stack_name" : object_stack_name, 
            "ip_address" : object_ip_address, "status" : object_status, "image_name" : object_image_name, "os" : object_os, "flavor_name" : object_flavor_name, "ram_size" : object_ram_size,
            "pc_spec" : object_pc_spec, "disk_size" : object_disk_size, "num_cpu" : object_num_cpu, "backup_time" : object_backup_time, "package" : object_package,"update_image" : object_update_image_id}
        instance_info = super().instance_backup_time_show(instance_info, object_instance_pk)
        print(instance_info)
        
        response = JsonResponse(instance_info, status=200)
        
        return response

# request django url = /openstack/log/<int:instance_pk>/
class InstanceLogShower(APIView):
    instance_pk = openapi.Parameter('instance_pk', openapi.IN_PATH, description='Instance ID to get info', required=True, type=openapi.TYPE_INTEGER)
    
    @swagger_auto_schema(tags=["Openstack Instance Log API"], manual_parameters=[openstack_user_token, instance_pk], responses={200:"Success", 401:"Unauthorized", 500:"Internal Server Error"})
    def get(self, request, instance_pk):
        try:
            if ServerStatusFlag.objects.get(platform_name="openstack").status == True:
                token, user_id = oc.getRequestParams(request)
            else:
                user_id = AccountInfo.objects.get(cloudstack_apiKey=request.headers["apiKey"]).user_id
            try:
                instance_log = list(InstanceLog.objects.filter(instance_pk=instance_pk).values())
            except Exception as e:
                print("인스턴스 정보 조회 중 예외 발생: ", e)
                return JsonResponse({"message" : "해당 가상머신이 존재하지 않습니다."}, status=404)

        except oc.TokenExpiredError as e:
            print("에러 내용: ", e)
            return JsonResponse({"message" : str(e)}, status=401)
        
        return JsonResponse({"log" : instance_log}, status=200)



# request django url = /openstack/dashboard/            대쉬보드에 리소스 사용량 보여주기 용
class DashBoard(RequestChecker, APIView):
    @swagger_auto_schema(tags=["Openstack Dashboard API"], manual_parameters=[openstack_user_token], responses={200:"Success", 401:"Unauthorized", 500:"Internal Server Error"})
    def get(self, request):     # header: user_token
        try:
            if ServerStatusFlag.objects.get(platform_name="openstack").status == True:
                token, user_id = oc.getRequestParams(request)
            else:
                user_id = AccountInfo.objects.get(cloudstack_apiKey=request.headers["apiKey"]).user_id

            try:
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


class InstanceStart(InstanceLogManager, Instance, APIView):
    @swagger_auto_schema(tags=["Openstack Instance API"], manual_parameters=[openstack_user_token], request_body=InstancePKSerializer, responses={202:"Accepted", 401:"Unauthorized", 404:"Not Found", 500:"Internal Server Error"})
    def post(self, request):    # header: user_token, body: instance_pk
        try:
            input_data, token, user_id = oc.getRequestParamsWithBody(request)   # 요청에는 user_id를 안쓰지만, exception 처리를 위해 user_id None인지 체크용으로 받아옴.
            if user_id == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 token으로 오픈스택 유저의 정보를 얻어올 수 없습니다."}, status=500)
            
            start_instance_pk = super().checkDataBaseInstanceID(input_data)
            start_instance_id = OpenstackInstance.objects.get(instance_pk=start_instance_pk).instance_id
            start_instance_name = OpenstackInstance.objects.get(instance_pk=start_instance_pk).instance_name
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
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 해당 동작을 수행할 수 없습니다."}, status=500)
            OpenstackInstance.objects.filter(instance_id=start_instance_id).update(status="ACTIVE")
            super().userLogAdder(user_id, start_instance_name, "Started", "instance")
            super().instanceLogAdder(input_data["instance_pk"], start_instance_name, "start", "Started")

        except oc.TokenExpiredError as e:
            print("에러 내용: ", e)
            return JsonResponse({"message" : str(e)}, status=401)
        
        return JsonResponse({"message" : "가상머신 시작"}, status=202)


class InstanceStop(InstanceLogManager, Instance, APIView):
    @swagger_auto_schema(tags=["Openstack Instance API"], manual_parameters=[openstack_user_token], request_body=InstancePKSerializer, responses={202:"Accepted", 401:"Unauthorized", 404:"Not Found", 500:"Internal Server Error"})
    def post(self, request):    # header: user_token, body: instance_pk
        try:
            input_data, token, user_id = oc.getRequestParamsWithBody(request)   # 요청에는 user_id를 안쓰지만, exception 처리를 위해 user_id None인지 체크용으로 받아옴.
            if user_id == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 token으로 오픈스택 유저의 정보를 얻어올 수 없습니다."}, status=500)

            stop_instance_pk = super().checkDataBaseInstanceID(input_data)
            stop_instance_id = OpenstackInstance.objects.get(instance_pk=stop_instance_pk).instance_id
            stop_instance_name = OpenstackInstance.objects.get(instance_pk=stop_instance_pk).instance_name
            if stop_instance_id == None :
                return JsonResponse({"message" : "인스턴스를 찾을 수 없습니다."}, status=404)

            server_stop_payload = {
                "os-stop" : None
            }
            instance_stop_req = super().reqCheckerWithData("post", "http://"+openstack_hostIP + "/compute/v2.1/servers/" + stop_instance_id
                + "/action", token, json.dumps(server_stop_payload))
            if instance_stop_req == None:    # "오픈스택과 통신이 안됐을 시(timeout 시)"
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 해당 동작을 수행할 수 없습니다."}, status=500)
            OpenstackInstance.objects.filter(instance_id=stop_instance_id).update(status="SHUTOFF")
            super().userLogAdder(user_id, stop_instance_name, "Stopped", "instance")
            super().instanceLogAdder(input_data["instance_pk"], stop_instance_name, "stop", "Stopped")

        except oc.TokenExpiredError as e:
            print("에러 내용: ", e)
            return JsonResponse({"message" : str(e)}, status=401)
        
        return JsonResponse({"message" : "가상머신 전원 끔"}, status=202)


class InstanceConsole(Instance, APIView):
    @swagger_auto_schema(tags=["Openstack Instance API"], manual_parameters=[openstack_user_token], request_body=InstancePKSerializer, responses={200:"Success", 401:"Unauthorized", 404:"Not Found", 500:"Internal Server Error"})
    def post(self, request):    # header: user_token, body: instance_pk
        try:
            input_data, token, user_id = oc.getRequestParamsWithBody(request)   # 요청에는 user_id를 안쓰지만, exception 처리를 위해 user_id None인지 체크용으로 받아옴.
            if user_id == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 token으로 오픈스택 유저의 정보를 얻어올 수 없습니다."}, status=500)

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
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 해당 동작을 수행할 수 없습니다."}, status=500)
        
            splitted_url = instance_console_req.json()["console"]["url"].split("/") # 인스턴스 콘솔 접속 IP를 가상머신 내부 네트워크 IP가 아닌 포트포워딩 해놨던 PC의 공인 IP로 바꾸기 위한 로직
            splitted_url[2] = oc.hostIP+":6080"
            instance_url = "/".join(splitted_url)
        

        except oc.TokenExpiredError as e:
            print("에러 내용: ", e)
            return JsonResponse({"message" : str(e)}, status=401)

        return JsonResponse({"instance_url" : instance_url}, status=200)        #git test



class ErrorPageView(Instance, APIView):
    @swagger_auto_schema(tags=["Instance Error Page API"], manual_parameters=[openstack_user_token], request_body=InstancePKSerializer, responses={200:"Success", 401:"Unauthorized", 404:"Not Found", 500:"Internal Server Error"})
    def post(self, request):    # header: user_token, body: instance_pk,   for error occur
        try:
            admin_token = oc.admin_token()
            input_data, user_token, user_id = oc.getRequestParamsWithBody(request)   # 요청에는 user_id를 안쓰지만, exception 처리를 위해 user_id None인지 체크용으로 받아옴.
            if user_id == None:
                    return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 token으로 오픈스택 유저의 정보를 얻어올 수 없습니다."}, status=500)
            instance_pk_for_error = super().checkDataBaseInstanceID(input_data)
            instance_id_for_error = OpenstackInstance.objects.get(instance_pk=instance_pk_for_error).instance_id

            instance_error_occur_payload = {
                "os-resetState" : {
                    "state" : "error"
                }
            }
            instance_error_occur_req = super().reqCheckerWithData("post", "http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_id_for_error+ "/action",
                admin_token, json.dumps(instance_error_occur_payload))
            if instance_error_occur_req == None:    # "오픈스택과 통신이 안됐을 시(timeout 시)"
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 해당 동작을 수행할 수 없습니다."}, status=500)
        
        except oc.TokenExpiredError as e:
            print("에러 내용: ", e)
            return JsonResponse({"message" : str(e)}, status=401)

        return JsonResponse({"message" : "가상머신 에러 발생시킴"}, status=200)        #git test


    @swagger_auto_schema(tags=["Instance Error Page API"], manual_parameters=[openstack_user_token], responses={200:"Success", 401:"Unauthorized", 404:"Not Found", 500:"Internal Server Error"})
    def get(self, request):     # header: user_token
        try:
            if ServerStatusFlag.objects.get(platform_name="openstack").status == False:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 리소스 정보를 받아올 수 없습니다."}, status=500)
            token, user_id = oc.getRequestParams(request)
            if user_id == None:
                return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 token으로 오픈스택 유저의 정보를 얻어올 수 없습니다."}, status=500)

            try:
                user_stack_data = list(OpenstackInstance.objects.filter(user_id=user_id).values())
                for stack_data in user_stack_data:
                    instance_pk = stack_data["instance_pk"]
                    stack_data = super().instance_backup_time_show(stack_data, instance_pk)
                print(user_stack_data)

            except OperationalError:
                return JsonResponse({[]}, status=200)
        
        except oc.TokenExpiredError as e:
            print("에러 내용: ", e)
            return JsonResponse({"message" : str(e)}, status=401)
        
        return JsonResponse({"instances" : user_stack_data}, status=200)