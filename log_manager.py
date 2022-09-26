from account.models import AccountInfo, AccountLog

def logAdder(user_id, obj, mode):
    insert_log = obj + " " + mode
    AccountLog.objects.create(
        user_id = AccountInfo.objects.get(user_id=user_id),
        log = insert_log
    )