import os      #여기서 부터
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))    #여기까지는 상위 디렉토리 모듈 import 하기 위한 코드

import openstack_controller as oc    #백엔드 루트 디렉토리에 openstack.py 생성했고, 그 안에 공통으로 사용될 함수, 변수들 넣을 것임.
from .openstack_modules import *
import json
import requests
from sqlite3 import OperationalError
from .models import OpenstackInstance
import account.models
from django.db.models import Sum
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils       import swagger_auto_schema
from drf_yasg             import openapi
from openstack.serializers import CreateStackSerializer, InstanceIDSerializer, OpenstackInstanceSerializer
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

class Openstack(TemplateModifier, APIView):
    @swagger_auto_schema(tags=['openstack api'], manual_parameters=[openstack_user_token], request_body=CreateStackSerializer, responses={200: "Success", 404: "Not Found", 405: "Method Not Allowed"})
    def post(self, request):
        input_data = json.loads(request.body)   # user_id, password, system_num(추후에 요구사항 폼 등으로 바뀌면 수정할 것)
        stack_template_root = "templates/"
        token = request.headers["X-Auth-Token"]
        user_id = oc.getUserID(token)
        if user_id == None:
            return JsonResponse({"message" : "오픈스택 서버에 문제가 생겼습니다."}, status=404)
        instance_num = OpenstackInstance.objects.filter(user_id=user_id).count() + 1
        
        user_os, user_package, flavor, user_instance_name, backup_time = super().getUserRequirement(input_data)
        if flavor == "EXCEEDED":
            return JsonResponse({"message" : "인원 수 X 인원 당 예상 용량 값은 10G를 넘지 못합니다."}, status=405)
        if backup_time != 6 and backup_time != 12 and backup_time != 24:
            return JsonResponse({"message" : "백업 주기는 6시간, 12시간, 24시간 중에서만 선택할 수 있습니다."}, status=405)
        

        openstack_tenant_id = account.models.Account_info.objects.get(user_id=user_id).openstack_user_project_id
        print("유저 프로젝트 id: ", openstack_tenant_id)

        if(user_os == "ubuntu"):
            with open(stack_template_root + 'ubuntu_1804.json','r') as f:   # 아직 템플릿 구현 안됨
                json_template_skeleton = json.load(f)
                json_template = super().templateModify(json_template_skeleton, user_id, user_instance_name, flavor, user_package, instance_num)
        elif(user_os == "cirros"):
            with open(stack_template_root + 'cirros.json','r') as f:    #일단 이거랑
                json_template_skeleton = json.load(f)
                json_template = super().templateModify(json_template_skeleton, user_id, user_instance_name, flavor, user_package, instance_num)
        elif(user_os == "fedora"):
            with open(stack_template_root + 'fedora.json','r') as f:    #이걸로 생성 test
                json_template_skeleton = json.load(f)
                json_template = super().templateModify(json_template_skeleton, user_id, user_instance_name, flavor, user_package, instance_num)
        
        #address heat-api v1 프로젝트 id stacks
        stack_req = requests.post("http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks",
            headers = {'X-Auth-Token' : token},
            data = json_template)
        print("stack생성", stack_req.json())
        stack_id = stack_req.json()["stack"]["id"]
        stack_name_req = requests.get("http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks?id=" + stack_id,
                            headers={'X-Auth-Token': token})
        print("스택 이름 정보: ", stack_name_req.json())
        stack_name = stack_name_req.json()["stacks"][0]["stack_name"]

        time.sleep(3)
        while(True):
            stack_resource_req = requests.get("http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks/" + stack_name + "/" # 스택으로 만든 인스턴스가 생성 완료될 때까지 기다림
                + stack_id + "/resources",
                headers = {'X-Auth-Token' : token}).json()["resources"]
            for resource in stack_resource_req: # 스택 리스폰스에서 리소스들의 순서가 바뀌어 오는 경우 발견. 순회로 해결함.
                if resource["resource_type"] == "OS::Nova::Server":
                    print("리소스 정보: ", resource)
                    resource_instance = resource
                    break
            if resource_instance["resource_status"] == "CREATE_COMPLETE":
                instance_id = resource_instance["physical_resource_id"]
                break
            time.sleep(2)

        print("인스턴스 id: ", instance_id)

        time.sleep(1)
        #인스턴스 정보 get, 여기서 image id, flavor id 받아와서 다시 get 요청해서 세부 정보 받아와야 함
        instance_info_req = requests.get("http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_id,
            headers = {'X-Auth-Token' : token})
        print("인스턴스 정보: ", instance_info_req.json())

        instance_name = instance_info_req.json()["server"]["name"]
        print("인스턴스 이름: ", instance_name)
        instance_ip_address = instance_info_req.json()["server"]["addresses"][user_id + "-net" + str(instance_num)][0]["addr"]
        print("인스턴스 ip: ",instance_ip_address)
        instance_status =  instance_info_req.json()["server"]["status"]
        print("인스턴스 상태: ",instance_status)
        image_id = instance_info_req.json()["server"]["image"]["id"]
        flavor_id = instance_info_req.json()["server"]["flavor"]["id"]

        image_req = requests.get("http://" + openstack_hostIP + "/compute/v2.1/images/" + image_id,
            headers = {'X-Auth-Token' : token})
        instance_image_name = image_req.json()["image"]["name"]
        print("이미지 이름: ", instance_image_name)

        flavor_req = requests.get("http://" + openstack_hostIP + "/compute/v2.1/flavors/" + flavor_id,
            headers = {'X-Auth-Token' : token})
        print(flavor_req)
        instance_flavor_name = flavor_req.json()["flavor"]["name"]
        print("flavor 이름: ", instance_flavor_name)
        instance_ram_size = round(flavor_req.json()["flavor"]["ram"]/953.7, 2)
        print("램 크기: ", instance_ram_size)
        instance_disk_size = flavor_req.json()["flavor"]["disk"]
        print("디스크 용량: ", instance_disk_size)
        instance_num_cpu = flavor_req.json()["flavor"]["vcpus"]
        print("CPU 개수: ", instance_num_cpu)

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
            "disk_size" : instance_disk_size,
            "num_cpu" : instance_num_cpu,
            "backup_time" : backup_time
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

        return JsonResponse({"message" : "가상머신 생성 완료"}, status=201)

    @swagger_auto_schema(tags=['openstack api'], manual_parameters=[openstack_user_token], responses={200: 'Success'})
    def get(self, request):
        token = request.headers["X-Auth-Token"]#oc.user_token(input_data)
        user_id = oc.getUserID(token)

        try:
            user_instance_info = OpenstackInstance.objects.filter(user_id=user_id)
            for instance_info in user_instance_info:
                # while(True):
                #     instance_req = requests.get("http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_info.instance_id,
                #     headers = {'X-Auth-Token' : token})
                #     instance_status = instance_req.json()["server"]["status"]
                #     if instance_status == OpenstackInstance.objects.filter(instance_id=instance_info.instance_id).status:
                #         break
                instance_req = requests.get("http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_info.instance_id,
                    headers = {'X-Auth-Token' : token})
                instance_status = instance_req.json()["server"]["status"]
                OpenstackInstance.objects.filter(instance_id=instance_info.instance_id).update(status=instance_status)

            user_stack_data = list(OpenstackInstance.objects.filter(user_id=user_id).values())
        except OperationalError:
            return JsonResponse({[]}, status=200)

        return JsonResponse({"instances" : user_stack_data}, status=200)

    #@swagger_auto_schema(tags=['openstack api'], manual_parameters=[openstack_user_token], request_body=CreateOpenstack, responses={200: 'Success'})    
    def put(self, request):
        pass
    
    #@swagger_auto_schema(tags=['openstack api'], manual_parameters=[openstack_user_token], request_body=CreateOpenstack, responses={200: 'Success'})
    def patch(self, request):
            
        pass

    @swagger_auto_schema(tags=['openstack api'], manual_parameters=[openstack_user_token], request_body=InstanceIDSerializer, responses={200: 'Success'})
    def delete(self, request):
        input_data = json.loads(request.body)   # user_id, password, instance_id
        token = request.headers["X-Auth-Token"]
        user_id = oc.getUserID(token)

        stack_data = OpenstackInstance.objects.get(instance_id=input_data["instance_id"])
        del_instance_name = stack_data.instance_name
        del_stack_name = stack_data.stack_name
        del_stack_id = stack_data.stack_id
        print("삭제한 가상머신 이름: " + del_instance_name + "\n삭제한 스택 이름: " + del_stack_name + "\n삭제한 스택 ID: " + del_stack_id)
        stack_data.delete() # DB에서 해당 stack row 삭제

        del_openstack_tenant_id = account.models.Account_info.objects.get(user_id=user_id).openstack_user_project_id
        stack_del_req = requests.delete("http://" + openstack_hostIP + "/heat-api/v1/" + del_openstack_tenant_id + "/stacks/"
            + del_stack_name + "/" + del_stack_id,
            headers = {'X-Auth-Token' : token})
        
        return JsonResponse({"message" : "가상머신 " + del_instance_name + " 삭제 완료"}, status=200)



class DashBoard(APIView):
    @swagger_auto_schema(tags=['Instance api'], manual_parameters=[openstack_user_token], responses={200: 'Success'})
    def get(self, request):
        token, user_id = oc.getRequestParams(request)

        try:
            user_instance_info = OpenstackInstance.objects.filter(user_id=user_id)
            for instance_info in user_instance_info:    # 대쉬보드 출력에 status는 굳이 필요없지만, db 정보 최신화를 위해 status 업데이트.
                instance_status_req = requests.get("http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_info.instance_id,
                    headers = {'X-Auth-Token' : token}).json()["server"]["status"]
                OpenstackInstance.objects.filter(instance_id=instance_info.instance_id).update(status=instance_status_req)

            num_instances = OpenstackInstance.objects.filter(user_id=user_id).count() 
            total_ram_size = OpenstackInstance.objects.filter(user_id=user_id).aggregate(Sum("ram_size"))
            total_disk_size = OpenstackInstance.objects.filter(user_id=user_id).aggregate(Sum("disk_size"))
            total_num_cpu = OpenstackInstance.objects.filter(user_id=user_id).aggregate(Sum("num_cpu"))
            #위에 애들 다 dict 형식.
            
            dashboard_data = {
                "num_instances" : num_instances,    # max = 10
                "total_ram_size" : total_ram_size["ram_size__sum"], # max = 50G
                "total_disk_size" : total_disk_size["disk_size__sum"],   # max = 1000G
                "total_num_cpu" : total_num_cpu["num_cpu__sum"]
            }

        except OperationalError:
            return JsonResponse({[]}, status=200)

        return JsonResponse(dashboard_data)



class InstanceStart(Instance, APIView):
    @swagger_auto_schema(tags=['Instance api'], manual_parameters=[openstack_user_token], request_body=InstanceIDSerializer, responses={200: 'Success'})
    def post(self, request):
        input_data, token, user_id = oc.getRequestParamsWithBody(request)   # 요청에는 user_id를 안쓰지만, exception 처리를 위해 user_id None인지 체크용으로 받아옴.
        if user_id == None:
            return JsonResponse({"message" : "오픈스택 서버에 문제가 생겼습니다."})
        
        start_instance_id = super().checkDataBaseInstanceID(input_data)
        if start_instance_id == None :
            return JsonResponse({"message" : "인스턴스를 찾을 수 없습니다."}, status=404)
        elif OpenstackInstance.objects.get(instance_id=start_instance_id).status == "ERROR" :
            return JsonResponse({"message" : "인스턴스가 ERROR 상태입니다."}, status=202)

        server_start_payload = {
            "os-start" : None
        }
        instance_start_req = requests.post("http://"+openstack_hostIP + "/compute/v2.1/servers/" + start_instance_id
            + "/action",
            headers = {'X-Auth-Token' : token},
            data = json.dumps(server_start_payload))
        
        return JsonResponse({"message" : "가상머신 시작"}, status=200)


class InstanceStop(Instance, APIView):
    @swagger_auto_schema(tags=['Instance api'], manual_parameters=[openstack_user_token], request_body=InstanceIDSerializer, responses={200: 'Success'})
    def post(self, request):
        input_data, token, user_id = oc.getRequestParamsWithBody(request)   # 요청에는 user_id를 안쓰지만, exception 처리를 위해 user_id None인지 체크용으로 받아옴.
        if user_id == None:
            return JsonResponse({"message" : "오픈스택 서버에 문제가 생겼습니다."})

        stop_instance_id = super().checkDataBaseInstanceID(input_data)
        if stop_instance_id == None :
            return JsonResponse({"message" : "인스턴스를 찾을 수 없습니다."}, status=404)

        server_stop_payload = {
            "os-stop" : None
        }
        instance_start_req = requests.post("http://"+openstack_hostIP + "/compute/v2.1/servers/" + stop_instance_id
            + "/action",
            headers = {'X-Auth-Token' : token},
            data = json.dumps(server_stop_payload))
        
        return JsonResponse({"message" : "가상머신 전원 끔"}, status=200)


class InstanceConsole(Instance, RequestChecker, APIView):
    @swagger_auto_schema(tags=['Instance api'], manual_parameters=[openstack_user_token], request_body=InstanceIDSerializer, responses={200: 'Success'})
    def post(self, request):
        input_data, token, user_id = oc.getRequestParamsWithBody(request)   # 요청에는 user_id를 안쓰지만, exception 처리를 위해 user_id None인지 체크용으로 받아옴.
        if user_id == None:
            return JsonResponse({"message" : "오픈스택 서버에 문제가 생겼습니다."})

        console_for_instance_id = super().checkDataBaseInstanceID(input_data)
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
            return JsonResponse({"message" : "오픈스택 서버에 문제가 생겼습니다."})
    
        splitted_url = instance_console_req.json()["console"]["url"].split("/") # 인스턴스 콘솔 접속 IP를 가상머신 내부 네트워크 IP가 아닌 포트포워딩 해놨던 PC의 공인 IP로 바꾸기 위한 로직
        splitted_url[2] = oc.hostIP+":6080"
        instance_url = "/".join(splitted_url)

        return JsonResponse({"instance_url" : instance_url}, status=200)