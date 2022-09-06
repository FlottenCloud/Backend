from django.db import models
from openstack.models import OpenstackInstance

# Create your models here.
class InstanceImgBoard(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    instance_img_file = models.FileField(max_length=255, blank=True, upload_to="img-files")
    
    class Meta:
        db_table = 'fileBoard'