from sqlite3 import OperationalError
import json
from bs4 import BeautifulSoup
import cloudstack_controller as csc
from log_manager import InstanceLogManager
from django.db.models import Q

from openstack.models import InstanceLog
from .models import CloudstackInstance
from account.models import AccountLog
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework.views import APIView
from account.models import AccountInfo
from drf_yasg.utils       import swagger_auto_schema
from drf_yasg             import openapi
from .serializers import CloudstackInstanceIDSerializer

cloudstack_hostID = csc.hostID
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

class Cloudstack(APIView):
    @swagger_auto_schema(tags=["Cloudstack API"], manual_parameters=[cloudstack_user_apiKey, cloudstack_user_secretKey], responses={200:"Success"})
    def get(self, request):  # header: apiKey, secretKey
        try:
            apiKey = request.headers["apiKey"]
            print(apiKey)
            secretKey = request.headers["secretKey"]
            cloudstack_user_id = AccountInfo.objects.filter(cloudstack_apiKey=apiKey)[0].user_id
            print(cloudstack_user_id)
            q = Q()     # Query를 통한 가상머신 검색을 위한 where 절
            query_instance_name = request.GET.get("instance_name", None)    # Query에 instance_name있는지 확인

            user_instance_info_list = list(CloudstackInstance.objects.filter(user_id=cloudstack_user_id).values())
            print(user_instance_info_list)

            if query_instance_name:   # Query에 가상머신 이름이 있으면
                q &= Q(instance_name=query_instance_name)   # where절을 통해 해당 가상머신만 추출
                print("Searched instance is")
                searched_instance = list(Cloudstack.objects.filter(q).values())
                print(searched_instance)
                return JsonResponse({"instance" : q}, status=200)

        except OperationalError:
            return JsonResponse({[]}, status=200)

        return JsonResponse({"instances": user_instance_info_list}, status=200)

# request django url = /cloudstack/<int:instance_pk>/
class CloudstackInstanceInfo(APIView):
    instance_pk = openapi.Parameter('instance_pk', openapi.IN_PATH, description='Instance ID to get info', required=True, type=openapi.TYPE_INTEGER)

    @swagger_auto_schema(tags=["Cloudstack Instance Info API"], manual_parameters=[instance_pk], responses={200:"Success", 404:"Not Found"})
    def get(self, request, instance_pk):
        apiKey = request.headers["apiKey"]
        user_id = AccountInfo.objects.filter(cloudstack_apiKey=apiKey)[0].user_id
        try:
            instance_object = CloudstackInstance.objects.get(instance_pk=instance_pk)
        except Exception as e:
            print("인스턴스 정보 조회 중 예외 발생: ", e)
            return JsonResponse({"message" : "해당 가상머신이 존재하지 않습니다."}, status=404)
        
        object_own_user_id = user_id
        object_instance_pk = instance_object.instance_pk
        object_instance_id = instance_object.instance_id
        object_instance_name = instance_object.instance_name
        object_ip_address = instance_object.ip_address
        object_status = instance_object.status
        object_flavor_name= instance_object.flavor_name
        object_ram_size = instance_object.ram_size
        object_disk_size = instance_object.disk_size
        object_num_cpu = instance_object.num_cpu
        instance_info = {"user_id" : object_own_user_id, "instance_pk" : object_instance_pk, "instance_id" : object_instance_id, "instance_name" : object_instance_name,
            "ip_address" : object_ip_address, "status" : object_status, "flavor_name" : object_flavor_name, "ram_size" : object_ram_size,
            "disk_size" : object_disk_size, "num_cpu" : object_num_cpu}
        print(instance_info)
        
        response = JsonResponse(instance_info, status=200)
        
        return response

# request django url = /cloudstack/log/<int:instance_pk>/
class CloudstackInstanceLogShower(APIView):
    instance_pk = openapi.Parameter('instance_pk', openapi.IN_PATH, description='Instance ID to get info', required=True, type=openapi.TYPE_INTEGER)

    @swagger_auto_schema(tags=["Cloudstack Instance Log API"], manual_parameters=[instance_pk], responses={200:"Success", 404:"Not Found"})
    def get(self, request, instance_pk):
        apiKey = request.headers["apiKey"]
        user_id = AccountInfo.objects.filter(cloudstack_apiKey=apiKey)[0].user_id
        try:
            instance_log = list(InstanceLog.objects.filter(instance_pk=instance_pk).values())
        except Exception as e:
            print("인스턴스 정보 조회 중 예외 발생: ", e)
            return JsonResponse({"message" : "해당 가상머신이 존재하지 않습니다."}, status=404)
 
        return JsonResponse({"log" : instance_log}, status=200)


# request django url = /openstack/dashboard/            대쉬보드에 리소스 사용량 보여주기 용
class DashBoard(APIView):
    @swagger_auto_schema(tags=["Cloudstack Dashboard API"], manual_parameters=[cloudstack_user_apiKey, cloudstack_user_secretKey], responses={200:"Success"})
    def get(self, request):     # header: apiKey, secretKey
        try:
            apiKey = request.headers["apiKey"]
            secretKey = request.headers["secretKey"]
            cloudstack_user_id = AccountInfo.objects.filter(cloudstack_apiKey=apiKey)[0].user_id

            num_instances = CloudstackInstance.objects.filter(user_id=cloudstack_user_id).count()
            total_ram_size = CloudstackInstance.objects.filter(user_id=cloudstack_user_id).aggregate(Sum("ram_size"))   # 여기서부터
            total_disk_size = CloudstackInstance.objects.filter(user_id=cloudstack_user_id).aggregate(Sum("disk_size"))
            total_num_cpu = CloudstackInstance.objects.filter(user_id=cloudstack_user_id).aggregate(Sum("num_cpu"))     # 여기까지 다 dict형식

            dashboard_data = {
                "num_instances" : num_instances,    # max = 10
                "total_ram_size" : total_ram_size["ram_size__sum"], # max = 50G
                "total_disk_size" : total_disk_size["disk_size__sum"],   # max = 1000G
                "total_num_cpu" : total_num_cpu["num_cpu__sum"]
            }

        except OperationalError:
            return JsonResponse({[]}, status=200)
        
        return JsonResponse(dashboard_data)


class InstanceStart(InstanceLogManager, APIView):
    @swagger_auto_schema(tags=["Cloudstack Instance API"], manual_parameters=[cloudstack_user_apiKey, cloudstack_user_secretKey], request_body=CloudstackInstanceIDSerializer, responses={202:"Accepted", 404:"Not Found"})
    def post(self, request):    # header: apiKey, secretKey, body: instance_id
        apiKey = request.headers["apiKey"]
        secretKey = request.headers["secretKey"]
        start_instance_pk = json.loads(request.body)["instance_pk"]
        user_id = CloudstackInstance.objects.get(instance_pk=start_instance_pk).user_id.user_id
        start_instance_id = CloudstackInstance.objects.get(instance_pk=start_instance_pk).instance_id
        start_instance_name = CloudstackInstance.objects.get(instance_pk=start_instance_pk).instance_name
        if start_instance_id == None :
            return JsonResponse({"message" : "인스턴스를 찾을 수 없습니다."}, status=404)

        instance_start_req_body = {"apiKey" : apiKey, "response" : "json", "command" : "startVirtualMachine", "hostid" : cloudstack_hostID, "id" : start_instance_id}
        instance_start_req = csc.requestThroughSig(secretKey, instance_start_req_body)
        
        CloudstackInstance.objects.filter(instance_id=start_instance_id).update(status="ACTIVE")
        super().userLogAdder(user_id, start_instance_name, "Started", "instance")
        super().instanceLogAdder(start_instance_pk, start_instance_name, "start", "Started")
        
        return JsonResponse({"message" : "가상머신 시작"}, status=202)

class InstanceStop(InstanceLogManager, APIView):
    @swagger_auto_schema(tags=["Cloudstack Instance API"], manual_parameters=[cloudstack_user_apiKey, cloudstack_user_secretKey], request_body=CloudstackInstanceIDSerializer, responses={202:"Accepted", 404:"Not Found"})
    def post(self, request):    # header: apiKey, secretKey, body: instance_id
        apiKey = request.headers["apiKey"]
        secretKey = request.headers["secretKey"]
        stop_instance_pk = json.loads(request.body)["instance_pk"]
        user_id = CloudstackInstance.objects.get(instance_pk=stop_instance_pk).user_id.user_id
        stop_instance_id = CloudstackInstance.objects.get(instance_pk=stop_instance_pk).instance_id
        stop_instance_name = CloudstackInstance.objects.get(instance_pk=stop_instance_pk).instance_name
        if stop_instance_id == None :
            return JsonResponse({"message" : "인스턴스를 찾을 수 없습니다."}, status=404)

        instance_stop_req_body = {"apiKey": apiKey, "response": "json", "command": "stopVirtualMachine", "id": stop_instance_id}
        instance_stop_req = csc.requestThroughSig(secretKey, instance_stop_req_body)
        
        CloudstackInstance.objects.filter(instance_id=stop_instance_id).update(status="SHUTOFF")
        super().userLogAdder(user_id, stop_instance_name, "Stopped", "instance")
        super().instanceLogAdder(stop_instance_pk, stop_instance_name, "stop", "Stopped")
        
        return JsonResponse({"message" : "가상머신 정지"}, status=202)

class InstanceConsole(APIView):
    @swagger_auto_schema(tags=["Cloudstack Instance API"], manual_parameters=[cloudstack_user_apiKey, cloudstack_user_secretKey], request_body=CloudstackInstanceIDSerializer, responses={202:"Accepted", 404:"Not Found"})
    def post(self, request):  # header: apiKey,secretKey, body: instance_id
        baseURL = "http://" + csc.hostIP + ":8080/client/console?"
        user_apiKey = request.headers["apiKey"]
        user_secretKey = request.headers["secretKey"]
        instance_pk = json.loads(request.body)["instance_pk"]
        instance_id = CloudstackInstance.objects.get(instance_pk=instance_pk).instance_id
        if instance_id == None :
            return JsonResponse({"message" : "인스턴스를 찾을 수 없습니다."}, status=404)

        request_body = {"vm": instance_id, "apiKey": user_apiKey, "response": "json", "cmd": "access"}
        console_URL_req = csc.requestThroughSigWithURL(baseURL, user_secretKey, request_body)
        htmlData = BeautifulSoup(console_URL_req, features="html.parser")
        console_url_body = htmlData.html.frameset.frame['src']
        console_URL = "http:" + console_url_body
        console_URL_split = console_URL.split("/")
        port = console_URL_split[5].split("&")
        port[1] = "port=6060"
        port_join = "&".join(port)
        externalIPwithPort=csc.hostIP.split(":")
        externalIP=externalIPwithPort[0]
        console_URL = "http://" + externalIP + "/" + console_URL_split[3] + "/" + console_URL_split[4] + "/" + port_join
        print("Console URL is : " + console_URL)

        return JsonResponse({"instance_url": console_URL}, status=200)