from rest_framework import serializers
from .models import OpenstackInstance, OpenstackBackupImage

class OpenstackInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpenstackInstance
        fields = ["user_id", "stack_id", "stack_name", "instance_id", "instance_name", "ip_address", "status", 
        "image_name", "flavor_name", "ram_size", "disk_size", "num_cpu", "backup_time"]

    def create(self, validated_data):
        return OpenstackInstance.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.user_id = validated_data.get('user_id', instance.user_id)
        instance.stack_id = validated_data.get('stack_id', instance.stack_id)
        instance.stack_name = validated_data.get('stack_name', instance.stack_name)
        instance.instance_id = validated_data.get('instance_id', instance.instance_id)
        instance.instance_name = validated_data.get('instance_name', instance.instance_name)
        instance.ip_address = validated_data.get('instance_ip_address', instance.instance_ip_address)
        instance.status = validated_data.get('instance_status', instance.instance_status)
        instance.image_name = validated_data.get('instance_image_name', instance.instance_image_name)
        instance.flavor_name = validated_data.get('flavor_name', instance.flavor_name)
        instance.ram_size = validated_data.get('ram_size', instance.ram_size)
        instance.disk_size = validated_data.get('disk_size', instance.disk_size)
        instance.num_cpu = validated_data.get('num_cpu', instance.num_cpu)
        instance.backup_time = validated_data.get('backup_time', instance.backup_time)
        instance.save()
        
        return instance

class OpenstackBackupImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpenstackBackupImage
        fields = ["instance_id", "image_id", "image_url"]

    def create(self, validated_data):
        return OpenstackBackupImage.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.instance_id = validated_data.get('instance_id', instance.instance_id)
        instance.image_id = validated_data.get('image_id', instance.image_id)
        instance.image_url = validated_data.get('image_url', instance.image_url)
        instance.save()
        
        return instance

class CreateStackSerializer(serializers.Serializer):
    system_num = serializers.IntegerField(help_text='system number', default="1")

class InstanceIDSerializer(serializers.Serializer):
    instance_id = serializers.CharField(help_text='instance id', default="1")