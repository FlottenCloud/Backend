import os
from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from .models import InstanceImgBoard
from openstack.models import OpenstackInstance
 
class InstanceImg(APIView):
    def post(self, request):
        # Saving the information in the database
        document = InstanceImgBoard(
            instance_img_file = request.FILES["imgFile"]
        )
        document.save()
        documents = InstanceImgBoard.objects.all()

        return JsonResponse({"현재까지 저장된 파일들: ", documents}, status=201)

    def get(self, request):
        path = request.GET['path']
        file_path = os.path.join(settings.MEDIA_ROOT, path)
    
        if os.path.exists(file_path):
            binary_file = open(file_path, 'rb')
            response = HttpResponse(binary_file.read(), content_type="application/octet-stream; charset=utf-8")
            response['Content-Disposition'] = 'attachment; filename=' + os.path.basename(file_path)
            return response
        else:
            message = '알 수 없는 오류가 발행하였습니다.'
            return HttpResponse("<script>alert('"+ message +"');history.back()'</script>")