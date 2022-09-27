from account.models import AccountInfo, AccountLog

def userLogAdder(user_id, mode):
    AccountLog.objects.create(
        user_id = AccountInfo.objects.get(user_id=user_id),
        agent = user_id,
        log = mode
    )

def instanceLogAdder(user_id, obj, mode):
    insert_log = mode + " " + obj
    AccountLog.objects.create(
        user_id = AccountInfo.objects.get(user_id=user_id),
        agent = obj,
        log = insert_log
    )