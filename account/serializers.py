from rest_framework import serializers


#------------------Swagger(For API specification)------------------#

class UserRegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(help_text="User's first name")
    last_name = serializers.CharField(help_text="User's last name")
    user_id = serializers.CharField(help_text="User's ID")
    email = serializers.EmailField(help_text="User's email")
    password = serializers.CharField(help_text="User's password")

# class UserInfoSeializer(serializers.Serializer):
#     user_id = serializers.CharField(help_text="User's ID")
#     email = serializers.EmailField(help_text="User's email")
#     first_name = serializers.CharField(help_text="User's first name")
#     last_name = serializers.CharField(help_text="User's last name")

# class UserDeleteSerializer(serializers.Serializer):
#     user_id = serializers.CharField(help_text="User's ID")

class UserSignInSerializer(serializers.Serializer):
    user_id = serializers.CharField(help_text="User's ID")
    password = serializers.CharField(help_text="User's password")