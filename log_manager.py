from account.models import AccountInfo, AccountLog

def userLogAdder(user_id, mode):
    insert_log = user_id + " " + mode
    AccountLog.objects.create(
        user_id = AccountInfo.objects.get(user_id=user_id),
        log = insert_log
    )

def instanceLogAdder(user_id, obj, mode):
    insert_log = mode + " " + obj
    AccountLog.objects.create(
        user_id = AccountInfo.objects.get(user_id=user_id),
        log = insert_log
    )