from rest_framework import serializers
from .models import OpenstackInstance

class OpenstackInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpenstackInstance
        fields = ["user_id", "stack_id", "stack_name", "instance_id", "instance_name", "ip_address", "status", 
        "image_name", "flavor_name", "ram_size", "disk_size", "num_cpu"]

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
        instance.save()
        
        return instance

class CreateStackSerializer(serializers.Serializer):
    system_num = serializers.IntegerField(help_text='system number', default="1")

class InstanceIDSerializer(serializers.Serializer):
    instance_id = serializers.CharField(help_text='instance id', default="1")
