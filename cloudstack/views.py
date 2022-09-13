from sqlite3 import OperationalError

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




