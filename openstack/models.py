import os   #여기서 부터
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))    #여기까지는 상위 디렉토리 모듈 import 하기 위한 코드

from django.db import models
from django.core.validators import MaxValueValidator
#import account

#account_model_info = "account_model.Account_info"

# Create your models here.
class OpenstackInstance(models.Model):  #유저와 연관짓기 위한 외래키 등록
    # Foreign key(user - stack info)
    user_id = models.ForeignKey("account.Account_info", related_name="user_resource_info", on_delete=models.CASCADE, db_column="user_id")
    # stack info
    instance_id = models.CharField(max_length = 50, primary_key = True) # backup image에서 외래키로 참조
    instance_name = models.CharField(max_length = 50)
    stack_id = models.CharField(max_length = 50)
    stack_name = models.CharField(max_length = 50)
    ip_address = models.GenericIPAddressField()
    status = models.CharField(max_length = 50)
    image_name = models.CharField(max_length = 50)
    flavor_name = models.CharField(max_length = 50)
    ram_size = models.FloatField(validators=[MaxValueValidator(12)])
    disk_size = models.FloatField(validators=[MaxValueValidator(100)])
    num_cpu = models.IntegerField(validators=[MaxValueValidator(12)])
    backup_time = models.IntegerField(validators=[MaxValueValidator(25)])

class OpenstackBackupImage(models.Model):
    # Foreign key(instance - backup image)
    instance_id = models.ForeignKey("OpenstackInstance", related_name="instance_backup_img", on_delete=models.CASCADE, db_column="instance_id")
    # backup image info
    image_id = models.CharField(max_length = 50, primary_key = True)
    image_url = models.CharField(max_length = 100)