from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import InstanceImgBoard

# Register your models here.

@admin.register(InstanceImgBoard)
class POSTAdmin(admin.ModelAdmin):
    list_display = ["instance_img_file", "created_at", "updated_at"]