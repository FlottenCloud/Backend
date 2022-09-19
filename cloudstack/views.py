from sqlite3 import OperationalError
import json
from bs4 import BeautifulSoup
import cloudstack_controller as csc
from .models import CloudstackInstance
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
            user_instance_info_list = list(CloudstackInstance.objects.filter(user_id=cloudstack_user_id).values())
            print(user_instance_info_list)

        except OperationalError:
            return JsonResponse({[]}, status=200)

        return JsonResponse({"instances": user_instance_info_list}, status=200)

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


class InstanceStart(APIView):
    @swagger_auto_schema(tags=["Cloudstack Instance API"], manual_parameters=[cloudstack_user_apiKey, cloudstack_user_secretKey], request_body=CloudstackInstanceIDSerializer, responses={202:"Accepted", 404:"Not Found"})
    def post(self, request):    # header: apiKey, secretKey, body: instance_id
        apiKey = request.headers["apiKey"]
        secretKey = request.headers["secretKey"]
        start_instance_id = json.loads(request.body)["instance_pk"]
        if start_instance_id == None :
            return JsonResponse({"message" : "인스턴스를 찾을 수 없습니다."}, status=404)

        instance_start_req_body = {"apiKey" : apiKey, "response" : "json", "command" : "startVirtualMachine", "hostid" : cloudstack_hostID, "id" : start_instance_id}
        instance_start_req = csc.requestThroughSig(secretKey, instance_start_req_body)
        
        CloudstackInstance.objects.filter(instance_id=start_instance_id).update(status="Running")
        
        return JsonResponse({"message" : "가상머신 시작"}, status=202)

class InstanceStop(APIView):
    @swagger_auto_schema(tags=["Cloudstack Instance API"], manual_parameters=[cloudstack_user_apiKey, cloudstack_user_secretKey], request_body=CloudstackInstanceIDSerializer, responses={202:"Accepted", 404:"Not Found"})
    def post(self, request):    # header: apiKey, secretKey, body: instance_id
        apiKey = request.headers["apiKey"]
        secretKey = request.headers["secretKey"]
        stop_instance_id = json.loads(request.body)["instance_pk"]
        if stop_instance_id == None :
            return JsonResponse({"message" : "인스턴스를 찾을 수 없습니다."}, status=404)

        instance_stop_req_body = {"apiKey": apiKey, "response": "json", "command": "stopVirtualMachine", "id": stop_instance_id}
        instance_stop_req = csc.requestThroughSig(secretKey, instance_stop_req_body)
        
        CloudstackInstance.objects.filter(instance_id=stop_instance_id).update(status="Stopped")
        
        return JsonResponse({"message" : "가상머신 정지"}, status=202)

class InstanceConsole(APIView):
    @swagger_auto_schema(tags=["Cloudstack Instance API"], manual_parameters=[cloudstack_user_apiKey, cloudstack_user_secretKey], request_body=CloudstackInstanceIDSerializer, responses={202:"Accepted", 404:"Not Found"})
    def post(self, request):  # header: apiKey,secretKey, body: instance_id
        baseURL = "http://10.125.70.28:8080/client/console?"
        user_apiKey = request.headers["apiKey"]
        user_secretKey = request.headers["secretKey"]
        instance_id = json.loads(request.body)["instance_pk"]
        if instance_id == None :
            return JsonResponse({"message" : "인스턴스를 찾을 수 없습니다."}, status=404)

        request_body = {"vm" : instance_id ,"apiKey": user_apiKey, "response" : "json" , "cmd": "access"}
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