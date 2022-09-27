from account.models import AccountInfo, AccountLog
from openstack.models import OpenstackInstance, InstanceLog

class UserLogManager:
    def userLogAdder(self, user_id, obj, behavior, mode):
        if mode == "user":
            AccountLog.objects.create(
                user_id = AccountInfo.objects.get(user_id=user_id),
                log = behavior
            )
        else:
            insert_log = behavior + " " + obj
            AccountLog.objects.create(
                user_id = AccountInfo.objects.get(user_id=user_id),
                log = insert_log
            )

class InstanceLogManager(UserLogManager):
    def instanceLogAdder(self, instance_pk, instance_name, behavior):
        InstanceLog.objects.create(
            instance_pk = OpenstackInstance.objects.get(instance_pk=instance_pk),
            instance_name = instance_name,
            log = behavior
        )