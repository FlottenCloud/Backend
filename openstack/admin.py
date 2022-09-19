from django.contrib import admin

from openstack.models import OpenstackBackupImage

# Register your models here.

@admin.register(OpenstackBackupImage)
class POSTAdmin(admin.ModelAdmin):
    list_display = ["instance_id", "image_id", "instance_img_file", "updated_at"]