import json

import channels.layers
from asgiref.sync import async_to_sync

from django.db.models.signals import post_save
from django.dispatch import receiver

from account.models import AccountLog
from openstack.models import InstanceLog, ServerLog

@receiver(post_save, sender=AccountLog)
def userLogMessage(sender, instance, **kwargs):
    channel_layer = channels.layers.get_channel_layer()
    user_id = instance.user_id.user_id
    # group_name = "user-{}".format(user_id)
    group_name = "user-AnonymousUser"

    message = {
        "user_id" : user_id,
        "added_log" : instance.log,
        "log_added_time" : str(instance.log_time)
    }

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type" : "user_log_send",
            "message" : message
        }
    )
    
@receiver(post_save, sender=InstanceLog)
def instanceLogMessage(sender, instance, **kwargs):
    channel_layer = channels.layers.get_channel_layer()
    user_id = instance.instance_pk.user_id.user_id
    # group_name = "user-{}".format(user_id)
    group_name = "user-AnonymousUser"
    instance_pk = instance.instance_pk.instance_pk
    instance_name = instance.instance_pk.instance_name

    message = {
        "user_id" : user_id,
        "instance_pk" : instance_pk,
        "instance_name" : instance_name,
        "action" : instance.action,     # 여기서 backup_start, backup_complete 등 판단
        "added_log" : instance.log,     # 이건 단순 log message라고 보면 됨.
        "log_added_time" : str(instance.log_time)
    }

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type" : "instance_log_send",
            "message" : message
        }
    )

@receiver(post_save, sender=ServerLog)
def serverLogMessage(sender, instance, **kwargs):
    channel_layer = channels.layers.get_channel_layer()
    # user_id = instance.instance_pk.user_id.user_id
    # group_name = "user-{}".format(user_id)
    group_name = "user-AnonymousUser"

    message = {
        "added_log" : instance.log,     # 이건 단순 log message라고 보면 됨.
        "log_added_time" : str(instance.log_time)
    }

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type" : "server_log_send",
            "message" : message
        }
    )