import os   #여기서 부터
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))    #여기까지는 상위 디렉토리 모듈 import 하기 위한 코드

import openstack_controler as oc    #백엔드 루트 디렉토리에 openstack.py 생성했고, 그 안에 공통으로 사용될 함수, 변수들 넣을 것임.
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponse

from openstack.serializers import OpenstackInstanceSerializer
from .models import OpenstackInstance
import json
import requests
import time
# Create your views here.
openstack_hostIP = oc.hostIP
openstack_tenant_id = "53db693b52494cdba387b1e5fa7c3cc7"#oc.admin_project_id

class openstack(APIView):
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
                json_data=json.load(f)
        elif(system_num==2):
            with open(stack_template_root + 'centos.json','r') as f:
                json_data=json.load(f)
        elif(system_num==3):
            with open(stack_template_root + 'fedora.json','r') as f:    #일단 이걸로 생성 test
                json_data=json.load(f)
        
        #address heat-api v1 프로젝트 id stacks
        stack_req = requests.post("http://"+openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks",
            headers = {'X-Auth-Token' : token},
            data = json.dumps(json_data))
        print("stack생성", stack_req.json())
        stack_id = stack_req.json()["stack"]["id"]
        stack_name_req = requests.get("http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks?id=" + stack_id,
                            headers={'X-Auth-Token': token})
        print(stack_name_req.json())
        stack_name = stack_name_req.json()["stacks"][0]["stack_name"]

        time.sleep(3)
        while(requests.get("http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks/" + stack_name + "/"
            + stack_id + "/resources",
            headers = {'X-Auth-Token' : token}).json()["resources"][0]["resource_status"] != "CREATE_COMPLETE"):
            time.sleep(2)

        stack_instance_req = requests.get("http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks/" + stack_name + "/"
            + stack_id + "/resources",
            headers = {'X-Auth-Token' : token})
        print(stack_instance_req.json())
        instance_id = stack_instance_req.json()["resources"][0]["physical_resource_id"]
        print(instance_id)
        #스택을 통해서 인스턴스 생성되기까지 시간이 좀 걸리는 듯. 일단 무지성 while문으로 해결은 했음..

        #인스턴스 정보 get, 여기서 image id, flavor id 받아와서 다시 get 요청해서 세부 정보 받아와야 함
        instance_info_req = requests.get("http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_id,
            headers = {'X-Auth-Token' : token})
        print(instance_info_req.json())

        instance_name = instance_info_req.json()["server"]["name"]
        print(instance_name)
        instance_ip_address = instance_info_req.json()["server"]["addresses"]["management-net"][0]["addr"]
        print(instance_ip_address)
        instance_status =  instance_info_req.json()["server"]["status"]
        print(instance_status)
        image_id = instance_info_req.json()["server"]["image"]["id"]
        flavor_id = instance_info_req.json()["server"]["flavor"]["id"]

        image_req = requests.get("http://" + openstack_hostIP + "/compute/v2.1/images/" + image_id,
            headers = {'X-Auth-Token' : token})
        instance_image_name = image_req.json()["image"]["name"]
        print(instance_image_name)

        flavor_req = requests.get("http://" + openstack_hostIP + "/compute/v2.1/flavors/" + flavor_id,
            headers = {'X-Auth-Token' : token})
        instance_flavor_name = flavor_req.json()["flavor"]["name"]
        print(instance_flavor_name)
        instance_ram_size = round(flavor_req.json()["flavor"]["ram"]*0.131072/1024, 2)
        print(instance_ram_size)

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
            "ram_size" : instance_ram_size
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
        # volume_id = instance_info_req.json()["server"]["os-extended-volumes:volumes_attached"][0]["id"]
        # volume_res = requests.get("http://" + openstack_hostIP + "/compute/v2.1/os-volumes/" + volume_id,
        #     headers = {'X-Auth-Token' : token})
        # disk_size = volume_res.json()["volume"]["size"]

        #print("ram: " + ram_size )#+ ", disk: " + disk_size)

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
        print(stack_del_req.json())
        
        return Response(stack_del_req.json())
