import json

from channels.generic.websocket import WebsocketConsumer

from django.db.models.signals import post_save
from django.dispatch import receiver

from account.models import AccountLog
from openstack.models import OpenstackInstance, InstanceLog
from cloudstack.models import CloudstackInstance

websocket = WebsocketConsumer()

@receiver(post_save, sender=AccountLog)
def userLogMessage(sender, instance, **kwargs):
    user_id = instance.user_id.user_id

    message = {
        "user_id" : user_id,
        "added_log" : instance.log,
        "log_added_time" : str(instance.log_time)
    }

    websocket.send(text_data=json.dumps({
        'type' : 'user_log',
        'message' : message
    }))

@receiver(post_save, sender=OpenstackInstance)
def openstackInstanceMessage(sender, instance, **kwargs):
    user_id = instance.user_id.user_id

    message = {
        "user_id" : user_id,
        "instance_pk" : instance.instance_pk,
        "instance_name" : instance.instance_name,
        "changed_status" : instance.status
    }

    websocket.send(text_data=json.dumps({
        'type' : 'openstack_instance_status_change',
        'message' : message
    }))

@receiver(post_save, sender=CloudstackInstance)
def cloudstackInstanceMessage(sender, instance, **kwargs):
    user_id = instance.user_id.user_id

    message = {
        "user_id" : user_id,
        "instance_pk" : instance.instance_pk,
        "instance_name" : instance.instance_name,
        "changed_status" : instance.status
    }

    websocket.send(text_data=json.dumps({
        'type' : 'cloudstack_instance_status_change',
        'message' : message
    }))
    
@receiver(post_save, sender=InstanceLog)
def instanceLogMessage(sender, instance, **kwargs):
    user_id = instance.instance_pk.user_id.user_id
    instance_pk = instance.instance_pk.instance_pk
    instance_name = instance.instance_pk.instance_name

    message = {
        "user_id" : user_id,
        "instance_pk" : instance_pk,
        "instance_name" : instance_name,
        "added_log" : instance.log,
        "log_added_time" : str(instance.log_time)
    }

    websocket.send(text_data=json.dumps({
        'type' : 'instance_log',
        'message' : message
    }))