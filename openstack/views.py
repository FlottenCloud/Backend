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
openstack_tenant_id = oc.project_id

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
        stack_req = requests.post("http://"+openstack_hostIP+"/heat-api/v1/"+openstack_tenant_id+"/stacks",
            headers = {'X-Auth-Token' : token},
            data = json.dumps(json_data))
        print("stack생성", stack_req.json())
        stack_id = stack_req.json()["stack"]["id"]

        time.sleep(3)
        while(requests.get("http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks/stack1/"
            + stack_id + "/resources",
            headers = {'X-Auth-Token' : token}).json()["resources"][0]["resource_status"] != "CREATE_COMPLETE"):
            time.sleep(2)

        stack_instance_req = requests.get("http://" + openstack_hostIP + "/heat-api/v1/" + openstack_tenant_id + "/stacks/stack1/"
            + stack_id + "/resources",
            headers = {'X-Auth-Token' : token})
        print(stack_instance_req.json())
        instance_id = stack_instance_req.json()["resources"][0]["physical_resource_id"]
        print(instance_id)
        #스택을 통해서 인스턴스 생성되기까지 시간이 좀 걸리는 듯. 일단 무지성 while문으로 해결은 했음..

        instance_info_req = requests.get("http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_id,
            headers = {'X-Auth-Token' : token})
        print(instance_info_req.json())
        flavor_id = instance_info_req.json()["server"]["flavor"]["id"]
        flavor_res = requests.get("http://" + openstack_hostIP + "/compute/v2.1/flavors/" + flavor_id,
            headers = {'X-Auth-Token' : token})
        ram_size = round(flavor_res.json()["flavor"]["ram"]*0.131072/1024, 2)
        print(ram_size)

        # volume_id = instance_info_req.json()["server"]["os-extended-volumes:volumes_attached"][0]["id"]
        # volume_res = requests.get("http://" + openstack_hostIP + "/compute/v2.1/os-volumes/" + volume_id,
        #     headers = {'X-Auth-Token' : token})
        # disk_size = volume_res.json()["volume"]["size"]

        #print("ram: " + ram_size )#+ ", disk: " + disk_size)

        return Response(stack_instance_req.json())

    def get(self, request): #스택 resources get 해오는 것 test
        token = oc.admin_token()
        user_res = requests.get("http://"+openstack_hostIP+"/heat-api/v1/"+openstack_tenant_id+"/stacks/stack1/"
            +"15626449-8e9b-40fe-a555-fa7488c55cef/resources",
            headers = {'X-Auth-Token' : token})
        instance_id = user_res.json()["resources"][0]["physical_resource_id"]
        print(user_res)

        # print(request.data)
        # flavor_volume_data = {
        #     "flavor_id" : flavor_id,
        #     "ram_size" : ram_size,
        #     "volume_size" : volume_size
        # }
        # # flavor_volume_data_JSON = json.dumps(flavor_volume_data)
        # # print(flavor_volume_data_JSON)
        # #print('{ "flavor_id" : "' + flavor_id + '", "volume_size" : "', volume_size, '" }')
        # #flavor_volume_data = '{ "flavor_id" : "' + flavor_id + '", "volume_size" : "', volume_size, '" }'
        # #flavor_volume_data_JSON = json.loads(flavor_volume_data)
        # #print(flavor_volume_data_JSON)

        # serializer = OpenstackInstanceSerializer(data=flavor_volume_data)
    
        # if serializer.is_valid():
        #     serializer.save()
        #     print("saved")
        #     print(serializer.data)
        # else:
        #     print("not saved")
        #     print(serializer.errors)

        return Response(user_res.json())#Response(serializer.data)
    
    def put(self, request):
        pass

    def delete(self, request):
        token = oc.admin_token()
        user_res = requests.delete("http://"+openstack_hostIP+"/heat-api/v1/"+openstack_tenant_id+"/stacks/"
            +"stack1/e689fd68-dfc6-4344-8c35-6ad908e8a194",
            headers = {'X-Auth-Token' : token})
        # instance_data = OpenstackInstance.objects.all()
        # instance_data.delete()
        return Response(user_res)
