from account.models import AccountInfo, AccountLog
from openstack.models import OpenstackInstance, InstanceLog, ServerLog

class UserLogManager:
    def userLogAdder(self, user_id, obj, log_message, mode):
        if mode == "user":
            AccountLog.objects.create(
                user_id = AccountInfo.objects.get(user_id=user_id),
                log = log_message
            )
        else:
            insert_log = log_message + " " + obj
            AccountLog.objects.create(
                user_id = AccountInfo.objects.get(user_id=user_id),
                log = insert_log
            )

class InstanceLogManager(UserLogManager):
    def instanceLogAdder(self, instance_pk, instance_name, instance_action, log_message):   # instance_action => create, update, start, stop, error_occurred, backup_start, backup_complete, restore_start, restore_complete
        InstanceLog.objects.create(
            instance_pk = OpenstackInstance.objects.get(instance_pk=instance_pk),
            instance_name = instance_name,
            action = instance_action,
            log = log_message
        )

class ServerLogManager(UserLogManager):
    def serverLogAdder(self, log_message):
        ServerLog.objects.create(
            log = log_message
        )