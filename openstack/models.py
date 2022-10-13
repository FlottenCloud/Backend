import os   #여기서 부터
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))    #여기까지는 상위 디렉토리 모듈 import 하기 위한 코드

from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
#import account

# Create your models here.
class OpenstackInstance(models.Model):  #유저와 연관짓기 위한 외래키 등록
    # Foreign key(user - stack info)
    user_id = models.ForeignKey("account.AccountInfo", related_name="user_resource_info", on_delete=models.CASCADE, db_column="user_id")
    # stack info
    instance_pk = models.AutoField(primary_key=True)
    instance_id = models.CharField(max_length=50) # backup image에서 외래키로 참조
    instance_name = models.CharField(max_length=50)
    stack_id = models.CharField(max_length=50, null=True)
    stack_name = models.CharField(max_length=50, null=True)
    ip_address = models.GenericIPAddressField()
    status = models.CharField(max_length=50)
    image_name = models.CharField(max_length=50)
    os = models.CharField(max_length=10)
    flavor_name = models.CharField(max_length=50)
    ram_size = models.FloatField(validators=[MaxValueValidator(12)])
    pc_spec = models.CharField(max_length=10, null=True)
    disk_size = models.FloatField(validators=[MaxValueValidator(100)])
    num_cpu = models.IntegerField(validators=[MaxValueValidator(12)])
    package = models.TextField(null=True, blank=True)
    backup_time = models.IntegerField(validators=[MaxValueValidator(25)])
    update_image_ID = models.CharField(max_length=100, null=True)   # 스택 처음 생성 시 update에 쓰인 image가 없음.
    freezer_completed = models.BooleanField(default=False)

    class Meta:
        db_table = 'openstack_instance'

class InstanceLog(models.Model):
    # Foreign key(instance - image-log)
    instance_pk = models.ForeignKey("OpenstackInstance", related_name="instance_log", on_delete=models.CASCADE, db_column="instance_pk")
    # instance log
    instance_name = models.CharField(max_length=50)
    action = models.TextField(null=True)     # 여기서 backup_start, backup_complete 등 판단
    log = models.TextField()    # 이건 단순 log message라고 보면 됨.
    log_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'instance_log'

class OpenstackBackupImage(models.Model):
    # Foreign key(instance - image-file)
    instance_pk = models.ForeignKey("OpenstackInstance", related_name="instance_backup_img_file", on_delete=models.CASCADE, db_column="instance_pk")
    # backup image file info
    image_id = models.CharField(max_length=50, primary_key=True)
    instance_id = models.CharField(max_length=50)
    image_url = models.CharField(max_length=100)
    instance_img_file = models.FileField(max_length=255, blank=True, upload_to="img-files")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'openstack_backup_image'

class ServerStatusFlag(models.Model):
    platform_name = models.CharField(max_length=50)
    status = models.BooleanField()

    class Meta:
        db_table = 'server_status'

class ServerLog(models.Model):
    log = models.CharField(max_length=200)
    log_time = models.DateTimeField(auto_now=True)

class DjangoServerTime(models.Model):
    start_time = models.TextField()
    backup_ran = models.BooleanField()
    backup_ran_time = models.TextField(null=True)

    class Meta:
        db_table = 'django_server_time'