import os   #여기서 부터
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))    #여기까지는 상위 디렉토리 모듈 import 하기 위한 코드

import openstack_controller as oc    #백엔드 루트 디렉토리에 openstack.py 생성했고, 그 안에 공통으로 사용될 함수, 변수들 넣을 것임.
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum

from openstack.serializers import OpenstackInstanceSerializer
from .models import OpenstackInstance
import json
import requests
import time
# Create your views here.
openstack_hostIP = oc.hostIP
openstack_tenant_id = "53db693b52494cdba387b1e5fa7c3cc7"#oc.admin_project_id

class Openstack(APIView):
    def post(self, request):
        input_data = json.loads(request.body)
        stack_template_root = "templates/"
        token = oc.user_token(input_data)
        system_num = input_data["system_num"]
        # stack_name= input("stack 이름 입력 : ")
        # key_name= input("key 이름 입력 : ")
        # server_name=1 input("server 이름 입력 : ") 
        # num_user=int(input("사용자 수 입력: ")) 

        if(system_num==1):
            with open(stack_template_root + 'main.json','r') as f:
                json_template=json.load(f)
        elif(system_num==2):
            with open(stack_template_root + 'centos.json','r') as f:
                json_template=json.load(f)
        elif(system_num==3):
            with open(stack_template_root + 'fedora.json','r') as f:    #일단 이걸로 생성 test
                json_template=json.load(f)
        
        #address heat-api v1 프로젝트 id stacks
        stack_req = requests.post("http://"+openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks",
            headers = {'X-Auth-Token' : token},
            data = json.dumps(json_template))
        print("stack생성", stack_req.json())
        stack_id = stack_req.json()["stack"]["id"]
        stack_name_req = requests.get("http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks?id=" + stack_id,
                            headers={'X-Auth-Token': token})
        print("스택 이름 정보: ", stack_name_req.json())
        stack_name = stack_name_req.json()["stacks"][0]["stack_name"]

        time.sleep(3)
        while(requests.get("http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks/" + stack_name + "/"
            + stack_id + "/resources",
            headers = {'X-Auth-Token' : token}).json()["resources"][0]["resource_status"] != "CREATE_COMPLETE"):
            time.sleep(2)

        stack_instance_req = requests.get("http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks/" + stack_name + "/"
            + stack_id + "/resources",
            headers = {'X-Auth-Token' : token})
        print("스택으로 만들어진 인스턴스 정보: ", stack_instance_req.json())
        instance_id = stack_instance_req.json()["resources"][1]["physical_resource_id"]
        print("인스턴스 id: ", instance_id)
        #스택을 통해서 인스턴스 생성되기까지 시간이 좀 걸리는 듯. 일단 무지성 while문으로 해결은 했음..

        time.sleep(1)
        #인스턴스 정보 get, 여기서 image id, flavor id 받아와서 다시 get 요청해서 세부 정보 받아와야 함
        instance_info_req = requests.get("http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_id,
            headers = {'X-Auth-Token' : token})
        print("인스턴스 정보: ", instance_info_req.json())

        instance_name = instance_info_req.json()["server"]["name"]
        print("인스턴스 이름: ", instance_name)
        instance_ip_address = instance_info_req.json()["server"]["addresses"]["management-net"][0]["addr"]
        print("인스턴스 ip: ",instance_ip_address)
        instance_status =  instance_info_req.json()["server"]["status"]
        print("인스턴스 상태: ",instance_status)
        image_id = instance_info_req.json()["server"]["image"]["id"]
        flavor_id = instance_info_req.json()["server"]["flavor"]["id"]
        volume_id = instance_info_req.json()["server"]["os-extended-volumes:volumes_attached"][0]["id"]

        image_req = requests.get("http://" + openstack_hostIP + "/compute/v2.1/images/" + image_id,
            headers = {'X-Auth-Token' : token})
        instance_image_name = image_req.json()["image"]["name"]
        print("이미지 이름: ", instance_image_name)

        flavor_req = requests.get("http://" + openstack_hostIP + "/compute/v2.1/flavors/" + flavor_id,
            headers = {'X-Auth-Token' : token})
        instance_flavor_name = flavor_req.json()["flavor"]["name"]
        print("flavor 이름: ", instance_flavor_name)
        instance_ram_size = round(flavor_req.json()["flavor"]["ram"]*0.131072/1024, 2)
        print("램 크기: ", instance_ram_size)

        volume_req = requests.get("http://" + openstack_hostIP + "/compute/v2.1/os-volumes/" + volume_id,
            headers = {'X-Auth-Token' : token})
        instance_disk_size = float(volume_req.json()["volume"]["size"])
        print("디스크 크기: ", instance_disk_size)

        # db에 저장 할 인스턴스 정보
        instance_data = {
            "stack_id" : stack_id,
            "stack_name" : stack_name,
            "instance_id" : instance_id,
            "instance_name" : instance_name,
            "ip_address" : str(instance_ip_address),
            "status" : instance_status,
            "image_name" : instance_image_name,
            "flavor_name" : instance_flavor_name,
            "ram_size" : instance_ram_size,
            "disk_size" : instance_disk_size
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

        return Response(serializer.data)

    def get(self, request): #스택 resources get 해오는 것 test
        token = oc.admin_token()
        user_res = requests.get("http://"+openstack_hostIP+"/heat-api/v1/"+openstack_tenant_id+"/stacks/stack1/"
            +"15626449-8e9b-40fe-a555-fa7488c55cef/resources",
            headers = {'X-Auth-Token' : token})
        instance_id = user_res.json()["resources"][0]["physical_resource_id"]
        print(user_res)

        return Response(user_res.json())#Response(serializer.data)
    
    def put(self, request):
        pass

    def delete(self, request):
        # del_data_all = OpenstackInstance.objects.all()
        # del_data_all.delete()
        input_data = json.loads(request.body)
        token = oc.user_token(input_data)
        del_stack_name = input_data["stack_name"]

        stack_data = OpenstackInstance.objects.get(stack_name = del_stack_name)
        del_stack_id = stack_data.stack_id
        print(del_stack_id)
        stack_data.delete()

        stack_del_req = requests.delete("http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks/"
            + del_stack_name + "/" + del_stack_id,
            headers = {'X-Auth-Token' : token})
        # print(stack_del_req.json())
        
        return Response(stack_del_req)

class DashBoard(APIView):
    def get(self, request):
        num_instances = OpenstackInstance.objects.count()
        total_ram_size = OpenstackInstance.objects.aggregate(Sum("ram_size"))
        total_disk_size = OpenstackInstance.objects.aggregate(Sum("disk_size"))
        # print(num_instances)
        # print(total_ram_size)
        # print(total_disk_size)
        dashboard_data = {
            "num_instances" : num_instances,
            "total_ram_size" : total_ram_size["ram_size__sum"],
            "total_disk_size" : total_disk_size["disk_size__sum"]
        }

        return JsonResponse(dashboard_data)

class InstanceStart(APIView):
    def post(self, request):
        input_data = json.loads(request.body)
        token = oc.user_token(input_data)
        start_instance_id = input_data["instance_id"]
        server_start_payload = {
            "os-start" : None
        }
        instance_start_req = requests.post("http://"+openstack_hostIP + "/compute/v2.1/servers/" + start_instance_id
            + "/action",
            headers = {'X-Auth-Token' : token},
            data = json.dumps(server_start_payload))
        OpenstackInstance.objects.filter(instance_id=start_instance_id).update(status="ACTIVE")
        
        return Response(instance_start_req)


class InstanceStop(APIView):
    def post(self, request):
        input_data = json.loads(request.body)
        token = oc.user_token(input_data)
        stop_instance_id = input_data["instance_id"]
        server_stop_payload = {
            "os-stop" : None
        }
        instance_start_req = requests.post("http://"+openstack_hostIP + "/compute/v2.1/servers/" + stop_instance_id
            + "/action",
            headers = {'X-Auth-Token' : token},
            data = json.dumps(server_stop_payload))
        OpenstackInstance.objects.filter(instance_id=stop_instance_id).update(status="SHUTOFF")
        
        return Response(instance_start_req)
