from rest_framework import serializers
from .models import OpenstackInstance

class OpenstackInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpenstackInstance
        fields = ["stack_id", "stack_name", "instance_id", "instance_name", "ip_address", "status", 
        "image_name", "flavor_name", "ram_size"]

    def create(self, validated_data):
        return OpenstackInstance.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.stack_id = validated_data.get('stack_id', instance.stack_id)
        instance.stack_name = validated_data.get('stack_name', instance.stack_name)
        instance.instance_id = validated_data.get('instance_id', instance.instance_id)
        instance.instance_name = validated_data.get('instance_name', instance.instance_name)
        instance.ip_address = validated_data.get('instance_ip_address', instance.instance_ip_address)
        instance.status = validated_data.get('instance_status', instance.instance_status)
        instance.image_name = validated_data.get('instance_image_name', instance.instance_image_name)
        instance.flavor_name = validated_data.get('flavor_name', instance.flavor_name)
        instance.ram_size = validated_data.get('ram_size', instance.ram_size)
        #instance.volume_size = validated_data.get('volume_size', instance.volume_size)
        instance.save()
        return instance