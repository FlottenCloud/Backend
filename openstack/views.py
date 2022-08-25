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
# Create your views here.
openstack_hostIP = oc.hostIP

class openstack(APIView):    #하나로 합치기
    def post(self, request):
        #input_data = json.loads(request.body)   #요구사항 및 생성할 인스턴스 이름 등? 대쉬보드에서 입력받은 정보의 body
        #admin_token = token()
        admin_token = oc.admin_token()
        flavor_id = "d1"
        instance_name = "django_test2"#input("생성할 인스턴스 이름 입력: ")
        # 특정 (shared) 네트워크 참조
        network_uuid = requests.get("http://" + openstack_hostIP + ":9696/v2.0/networks?name=public",
            headers = {'X-Auth-Token' : admin_token}
            ).json()["networks"][0]["id"]
        #print(network_uuid)
        # print()
        # print("network uuid : "+network_uuid)
        # print()

        # 특정 img id 참조
        # img_uuid = requests.get("http://" + openstack_hostIP + "/image/v2/images?name=ubuntu",  #해당 이미지는 내 서버에 없으므로 수정할 것
        #     headers = {'X-Auth-Token' : admin_token}
        #     ).json()["images"][0]["id"]

        
        # flavor_reference= input("flavor ref id 입력: ")
        openstack_instance_payload = {
            "server" : {
                "name" : instance_name,
                "imageRef" : "d7626315-8f03-4fd6-9938-d9d208440136",#img_uuid,
                "flavorRef" : flavor_id,
                "networks" : [{
                    "uuid" : network_uuid
                }]
            }
        }
        #인스턴스 생성 요청
        user_res = requests.post("http://" + openstack_hostIP + "/compute/v2.1/servers",
            headers = {'X-Auth-Token' : admin_token},
            data = json.dumps(openstack_instance_payload))
        # print(user_res.json())

        return Response(user_res.json())

    def get(self, request): #임시로 인스턴스 정보 get 해오는 것 test
        admin_token = oc.admin_token()
        instance_id = "8f2a7448-6942-461b-a524-0c9990b8346b"
        user_res = requests.get("http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_id,
            headers = {'X-Auth-Token' : admin_token})


        
        print("flavor_id: ", user_res.json()["server"]["flavor"]["id"])
        flavor_id = user_res.json()["server"]["flavor"]["id"]
        flavor_res = requests.get("http://" + openstack_hostIP + "/compute/v2.1/flavors/" + flavor_id,
            headers = {'X-Auth-Token' : admin_token})
        ram_size_Mib = flavor_res.json()["flavor"]["ram"]
        ram_size = round((ram_size_Mib*0.131072)/1024, 2)  #Mib를 Gb로 변환


        volume_id = user_res.json()["server"]["os-extended-volumes:volumes_attached"][0]["id"]
        volume_res = requests.get("http://" + openstack_hostIP + "/compute/v2.1/os-volumes/" + volume_id,
            headers = {'X-Auth-Token' : admin_token})
        
        print("volume size : ", volume_res.json()["volume"]["size"])
        volume_size = volume_res.json()["volume"]["size"]

        print(request.data)
        flavor_volume_data = {
            "flavor_id" : flavor_id,
            "ram_size" : ram_size,
            "volume_size" : volume_size
        }
        # flavor_volume_data_JSON = json.dumps(flavor_volume_data)
        # print(flavor_volume_data_JSON)
        #print('{ "flavor_id" : "' + flavor_id + '", "volume_size" : "', volume_size, '" }')
        #flavor_volume_data = '{ "flavor_id" : "' + flavor_id + '", "volume_size" : "', volume_size, '" }'
        #flavor_volume_data_JSON = json.loads(flavor_volume_data)
        #print(flavor_volume_data_JSON)

        serializer = OpenstackInstanceSerializer(data=flavor_volume_data)
    
        if serializer.is_valid():
            serializer.save()
            print("saved")
            print(serializer.data)
        else:
            print("not saved")
            print(serializer.errors)

        return Response(serializer.data)#Response(user_res.json())#Response(serializer.data)
    
    def put(self, request):
        pass

    def delete(self, request):
        instance_data = OpenstackInstance.objects.all()
        instance_data.delete()
        return HttpResponse("Del Success")
