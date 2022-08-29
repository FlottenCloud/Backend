import os   #여기서 부터
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))    #여기까지는 상위 디렉토리 모듈 import 하기 위한 코드

from django.db import models
from django.core.validators import MaxValueValidator
import account

#account_model_info = "account_model.Account_info"

# Create your models here.
class OpenstackInstance(models.Model):  #유저와 연관짓기 위한 외래키 등록
    user_id = models.ForeignKey("account.Account_info", related_name="user_resource_info", on_delete=models.CASCADE, db_column="user_id", null = True)

    stack_id = models.CharField(max_length = 50, primary_key = True)
    stack_name = models.CharField(max_length = 50, null = True)
    instance_id = models.CharField(max_length = 50, null = True)
    instance_name = models.CharField(max_length = 50, null = True)
    ip_address = models.GenericIPAddressField(null = True)
    status = models.CharField(max_length = 50, null = True)
    image_name = models.CharField(max_length = 50, null = True)
    flavor_name = models.CharField(max_length = 50, null = True)
    ram_size = models.FloatField(validators=[MaxValueValidator(12)])
    disk_size = models.FloatField(validators=[MaxValueValidator(100)], null = True)