from django.db import models

from django.core.validators import MinValueValidator
# Create your models here.

class AccountInfo(models.Model):
    # user info
    user_id = models.CharField(max_length=50, primary_key=True)
    email = models.EmailField(max_length=50)
    password = models.CharField(max_length=100)
    first_name = models.CharField(max_length=10)
    last_name = models.CharField(max_length=10)
    openstack_user_id = models.CharField(max_length=100)
    openstack_user_project_id = models.CharField(max_length=100)
    cloudstack_account_id = models.CharField(max_length=100)
    cloudstack_apiKey = models.CharField(max_length=200)
    cloudstack_secretKey = models.CharField(max_length=200)
    cloudstack_network_id = models.CharField(max_length=200)
    cloudstack_network_vlan = models.IntegerField(validators=[MinValueValidator(100)])

    class Meta:
        db_table = 'accounts_info'

class AccountLog(models.Model):
    # Foreign Key
    user_id = models.ForeignKey("AccountInfo", related_name="user_log", on_delete=models.CASCADE, db_column="user_id")
    # log
    log = models.TextField()
    log_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_log'