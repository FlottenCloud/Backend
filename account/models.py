from django.db import models
# Create your models here.

class Account_info(models.Model):
    # user info
    user_id = models.CharField(max_length=50, primary_key=True)
    email = models.EmailField(max_length=50)
    password = models.CharField(max_length=100)
    openstack_user_id = models.CharField(max_length=100)
    openstack_user_project_id = models.CharField(max_length=100)
    token = models.CharField(max_length=200)
    # api_key = models.CharField(max_length=200)
    # secret_key = models.CharField(max_length=200)

    class Meta:
        #table name
        db_table = 'accounts_info'
