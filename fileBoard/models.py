from django.db import models
from openstack.models import OpenstackInstance

# Create your models here.
class InstanceImgBoard(models.Model):
    # Foreign key(instance - image-file)
    instance_id = models.ForeignKey("openstack.OpenstackInstance", related_name="instance_backup_img_file", on_delete=models.CASCADE, db_column="instance_id")
    # backup image file info
    image_id = models.CharField(max_length = 50, primary_key = True)
    instance_img_file = models.FileField(max_length=255, blank=True, upload_to="img-files")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'fileBoard'