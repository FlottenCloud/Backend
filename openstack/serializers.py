from rest_framework import serializers
from .models import OpenstackInstance

class OpenstackInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpenstackInstance
        fields = ['flavor_id', 'volume_size']

    def create(self, validated_data):
        return OpenstackInstance.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.flavor_id = validated_data.get('flavor_id', instance.flavor_id)
        instance.volume_size = validated_data.get('volume_size', instance.volume_size)
        instance.save()
        return instance