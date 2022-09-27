from django.core.validators import MaxValueValidator
from django.db import models

class CloudstackInstance(models.Model):  #유저와 연관짓기 위한 외래키 등록
    # Foreign key(user - cloudstack instance info)
    user_id = models.ForeignKey("account.AccountInfo", related_name="user_cloudstack_resource_info", on_delete=models.CASCADE, db_column="user_id")
    # cloudstack instance info
    instance_id = models.CharField(max_length=50, primary_key=True) # backup image에서 외래키로 참조
    instance_pk = models.IntegerField(null=False)
    instance_name = models.CharField(max_length=50)      # display name
    ip_address = models.GenericIPAddressField()        # public ip
    status = models.CharField(max_length=50)              # state
    image_id = models.CharField(max_length=50)      # template id
    flavor_name = models.CharField(max_length=50)   # service offering name
    ram_size = models.FloatField(validators=[MaxValueValidator(12)])    # memory
    disk_size = models.FloatField(validators=[MaxValueValidator(100)])      #size(byte로 온다 -> GIB 변환 %(1024)^3  (query : virtual machine id, listVolumes)
    num_cpu = models.IntegerField(validators=[MaxValueValidator(12)])       # cpu number
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cloudstack_instance'