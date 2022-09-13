from rest_framework import serializers


#------------------Swagger(For API specification)------------------#

class CloudstackInstanceIDSerializer(serializers.Serializer):
    instance_id = serializers.CharField(help_text="Instance's ID want to control.")