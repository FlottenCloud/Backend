from rest_framework import serializers
from .models import OpenstackInstance, OpenstackBackupImage


#------------------For Instance Control------------------#

class OpenstackInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpenstackInstance
        fields = ["user_id", "instance_pk", "stack_id", "stack_name", "instance_id", "instance_name", "ip_address", "status", 
        "image_name", "flavor_name", "ram_size", "pc_spec", "disk_size", "num_cpu", "package", "backup_time", "os"]

    def create(self, validated_data):
        return OpenstackInstance.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.user_id = validated_data.get("user_id", instance.user_id)
        instance.instance_pk = validated_data.get("instance_pk", instance.instance_pk)
        instance.stack_id = validated_data.get("stack_id", instance.stack_id)
        instance.stack_name = validated_data.get("stack_name", instance.stack_name)
        instance.instance_id = validated_data.get("instance_id", instance.instance_id)
        instance.instance_name = validated_data.get("instance_name", instance.instance_name)
        instance.ip_address = validated_data.get("instance_ip_address", instance.instance_ip_address)
        instance.status = validated_data.get("instance_status", instance.instance_status)
        instance.image_name = validated_data.get("instance_image_name", instance.instance_image_name)
        instance.flavor_name = validated_data.get("flavor_name", instance.flavor_name)
        instance.ram_size = validated_data.get("ram_size", instance.ram_size)
        instance.pc_spec = validated_data.get("pc_spec", instance.pc_spec)
        instance.disk_size = validated_data.get("disk_size", instance.disk_size)
        instance.num_cpu = validated_data.get("num_cpu", instance.num_cpu)
        instance.package = validated_data.get("package", instance.package)
        instance.backup_time = validated_data.get("backup_time", instance.backup_time)
        instance.os = validated_data.get("os", instance.os)
        instance.save()
        
        return instance


#------------------For Instance Backup------------------#

class OpenstackBackupImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpenstackBackupImage
        fields = ["instance_pk", "instance_id", "image_id", "image_url", "instance_img_file"]

    def create(self, validated_data):
        return OpenstackBackupImage.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.instance_pk = validated_data.get("instance_pk", instance.instance_pk)
        instance.instance_id = validated_data.get("instance_id", instance.instance_id)
        instance.image_id = validated_data.get("image_id", instance.image_id)
        instance.image_url = validated_data.get("image_url", instance.image_url)
        instance.instance_img_file = validated_data.get("instance_img_file", instance.instance_img_file)
        instance.save()
        
        return instance

#------------------Swagger(For API specification)------------------#

class CreateStackSerializer(serializers.Serializer):
    os = serializers.CharField(help_text="OS(centos, fedora, ubuntu) user want to use.", default="fedora")
    package = serializers.ListField(help_text="Package(apache2, default-jdk, ftp, libguestfs-tools, net-tools, pastebinit, pwgen, vim) user want to install. User can choice nothing.", default=[])
    pc_spec = serializers.CharField(help_text="Instance's spec")
    instance_name = serializers.CharField(help_text="Instance name user want to set.")
    backup_time = serializers.IntegerField(help_text="Instance's backup time(6, 12) user want to set.", default=6)

class UpdateStackSerializer(serializers.Serializer):
    instance_pk = serializers.IntegerField(help_text="Instance's pk want to control.")
    package = serializers.ListField(help_text="Package(apache2, default-jdk, ftp, libguestfs-tools, net-tools, pastebinit, pwgen, vim) user want to install. User can choice nothing.", default=[])
    pc_spec = serializers.CharField(help_text="Instance's spec")
    backup_time = serializers.IntegerField(help_text="Instance's backup time(6, 12) user want to set.", default=6)


class InstancePKSerializer(serializers.Serializer):
    instance_pk = serializers.IntegerField(help_text="Instance's pk want to control.")