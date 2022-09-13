from sqlite3 import OperationalError
import json
import cloudstack_controller as csc
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework.views import APIView
from account.models import AccountInfo
from .models import CloudstackInstance
import cloudstack_controller as csc

class Cloudstack(APIView):
    def get(self, request):  # header: user_token
        try:
            apiKey = request.headers["apiKey"]
            secretKey = request.headers["secretKey"]
            cloudstack_user_id = AccountInfo.objects.filter(cloudstack_apiKey=apiKey)[0].user_id
            user_instance_info_list = list(CloudstackInstance.objects.filter(user_id=cloudstack_user_id).values())
            #cloud stack DB 최신화는 ㄴㄴ

        except OperationalError:
            return JsonResponse({[]}, status=200)

        return JsonResponse({"instances": user_instance_info_list}, status=200)

# # request django url = /openstack/dashboard/            대쉬보드에 리소스 사용량 보여주기 용
# class DashBoard(RequestChecker, APIView):
#     @swagger_auto_schema(tags=["Instance api"], manual_parameters=[openstack_user_token], responses={200:"Success", 404:"Not Found"})
#     def get(self, request):     # header: user_token
#         try:
#             token, user_id = oc.getRequestParams(request)
#             if user_id == None:
#                 return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 token으로 오픈스택 유저의 정보를 얻어올 수 없습니다."}, status=404)

#             try:
#                 user_instance_info = OpenstackInstance.objects.filter(user_id=user_id)
#                 for instance_info in user_instance_info:    # 대쉬보드 출력에 status는 굳이 필요없지만, db 정보 최신화를 위해 status 업데이트.
#                     instance_status_req = super().reqChecker("get", "http://" + openstack_hostIP + "/compute/v2.1/servers/" + instance_info.instance_id, token)
#                     if instance_status_req == None:
#                         return JsonResponse({"message" : "오픈스택 서버에 문제가 생겨 리소스 정보를 받아올 수 없습니다."}, status=404)

#                     instance_status = instance_status_req.json()["server"]["status"]
#                     OpenstackInstance.objects.filter(instance_id=instance_info.instance_id).update(status=instance_status)

#                 num_instances = OpenstackInstance.objects.filter(user_id=user_id).count()
#                 total_ram_size = OpenstackInstance.objects.filter(user_id=user_id).aggregate(Sum("ram_size"))   # 여기서부터
#                 total_disk_size = OpenstackInstance.objects.filter(user_id=user_id).aggregate(Sum("disk_size"))
#                 total_num_cpu = OpenstackInstance.objects.filter(user_id=user_id).aggregate(Sum("num_cpu")) # 여기까지 다 dict형식
                
#                 dashboard_data = {
#                     "num_instances" : num_instances,    # max = 10
#                     "total_ram_size" : total_ram_size["ram_size__sum"], # max = 50G
#                     "total_disk_size" : total_disk_size["disk_size__sum"],   # max = 1000G
#                     "total_num_cpu" : total_num_cpu["num_cpu__sum"]
#                 }

#             except OperationalError:
#                 return JsonResponse({[]}, status=200)
        

#         except oc.TokenExpiredError as e:
#             print("에러 내용: ", e)
#             return JsonResponse({"message" : str(e)}, status=401)

#         return JsonResponse(dashboard_data)



class InstanceStart(APIView):
    # @swagger_auto_schema(tags=["Instance api"], manual_parameters=[openstack_user_token], request_body=InstanceIDSerializer, responses={202:"Accepted", 404:"Not Found"})
    def post(self, request):    # header: user_token, body: instance_id
        input_data = json.loads(request.body)
        instance_id = input_data["instance_id"]
        apiKey = request.headers["apiKey"]
        secretKey = request.headers["secretKey"]
        
        start_instance_id = instance_id
        if start_instance_id == None :
            return JsonResponse({"message" : "인스턴스를 찾을 수 없습니다."}, status=404)

        instance_start_req_body = {"apiKey": apiKey, "response": "json", "command": "startVirtualMachine", "id": start_instance_id}
        instance_start_req = csc.requestThroughSig(secretKey, instance_start_req_body)
        
        return JsonResponse({"message" : "가상머신 시작"}, status=202)


class InstanceStop(RequestChecker, Instance, APIView):
    # @swagger_auto_schema(tags=["Instance api"], manual_parameters=[openstack_user_token], request_body=InstanceIDSerializer, responses={202:"Accepted", 404:"Not Found"})
    def post(self, request):    # header: user_token, body: instance_id
        input_data = json.loads(request.body)
        instance_id = input_data["instance_id"]
        apiKey = request.headers["apiKey"]
        secretKey = request.headers["secretKey"]
        
        start_instance_id = instance_id
        if start_instance_id == None :
            return JsonResponse({"message" : "인스턴스를 찾을 수 없습니다."}, status=404)

        instance_stop_req_body = {"apiKey": apiKey, "response": "json", "command": "stopVirtualMachine", "id": start_instance_id}
        instance_stop_req = csc.requestThroughSig(secretKey, instance_stop_req_body)
        
        return JsonResponse({"message" : "가상머신 시작"}, status=202)

class InstanceConsole(APIView):
    def post(self, request):  # header: apiKey,secretKey, body: instance_id

        baseURL = "http://119.198.160.6:8080/client/console?"   #다른 메소드들과 달리 마지막 api? 가 아닌 console?이다.
        user_apiKey = request.headers["apiKey"]
        user_secretKey = request.headers["secretKey"]
        instance_id = request.body["instance_id"]

        request_body = {"vm" : instance_id ,"apiKey": user_apiKey, "response" : "json" , "cmd": "access"}
        console_URL = csc.requestThroughSigWithURL(baseURL, user_secretKey, request_body)
        print(console_URL)
        return JsonResponse({"instance_url": console_URL}, status=200)
