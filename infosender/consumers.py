import json
import logging
from channels.generic.websocket import WebsocketConsumer
from django.db.models.signals import post_save
from django.dispatch import receiver

from account.models import AccountLog
from openstack.models import OpenstackInstance, InstanceLog
from cloudstack.models import CloudstackInstance

class InfoConsumer(WebsocketConsumer):
    logger = logging.getLogger(__name__)

    def connect(self):
        self.accept()

        self.send(text_data=json.dumps({
            "type" : "connection_established",
            "message" : "Connected to 뜬구름"
        }))
   
    # def receive(self, text_data):
    #     text_data_json = json.loads(text_data)
    #     message = text_data_json['message']
    #     print(message)
    #     self.chat_message(text_data_json)

    # def chat_message(self, event):
    #     message = event['message']

    #     self.send(text_data=json.dumps({
    #         'type':'chat',
    #         'message':message
    #     }))

    @receiver(post_save, sender=AccountLog)
    def userLogMessage(self, instance, **kwargs):
        self.logger.debug("Log modified: {} :: content = {}.".format(instance, instance.content))

        user_id = instance.user_id.user_id

        message = {
            "user_id" : user_id,
            "added_log" : instance.log,
            "log_added_time" : instance.log_time
        }

        self.send(text_data=json.dumps({
            'type' : 'user_log',
            'message' : message
        }))

    @receiver(post_save, sender=OpenstackInstance)
    def openstackInstanceMessage(self, instance, **kwargs):
        self.logger.debug("Log modified: {} :: content = {}.".format(instance, instance.content))

        user_id = instance.user_id.user_id

        message = {
            "user_id" : user_id,
            "instance_pk" : instance.instance_pk,
            "instance_name" : instance.instance_name,
            "changed_status" : instance.status
        }

        self.send(text_data=json.dumps({
            'type' : 'openstack_instance_status_change',
            'message' : message
        }))

    @receiver(post_save, sender=CloudstackInstance)
    def cloudstackInstanceMessage(self, instance, **kwargs):
        self.logger.debug("Log modified: {} :: content = {}.".format(instance, instance.content))

        user_id = instance.user_id.user_id

        message = {
            "user_id" : user_id,
            "instance_pk" : instance.instance_pk,
            "instance_name" : instance.instance_name,
            "changed_status" : instance.status
        }

        self.send(text_data=json.dumps({
            'type' : 'cloudstack_instance_status_change',
            'message' : message
        }))
        
    @receiver(post_save, sender=InstanceLog)
    def instanceLogMessage(self, instance, **kwargs):
        self.logger.debug("Log modified: {} :: content = {}.".format(instance, instance.content))

        user_id = instance.instance_pk.user_id.user_id
        instance_pk = instance.instance_pk.instance_pk
        instance_name = instance.instance_pk.instance_name

        message = {
            "user_id" : user_id,
            "instance_pk" : instance_pk,
            "instance_name" : instance_name,
            "added_log" : instance.log,
            "log_added_time" : instance.log_time
        }

        self.send(text_data=json.dumps({
            'type' : 'instance_log',
            'message' : message
        }))