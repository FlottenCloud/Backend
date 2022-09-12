from sqlite3 import OperationalError

from django.http import JsonResponse
from django.shortcuts import render
from rest_framework.views import APIView
from account.models import AccountInfo
from .models import CloudstackInstance

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

