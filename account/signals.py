import json
import logging

import channels
from asgiref.sync import async_to_sync

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AccountLog


logger = logging.getLogger(__name__)  # pylint: disable=C0103


@receiver(post_save, sender=AccountLog, dispatch_uid='update_user_log_listeners')
def update_user_log_listeners(sender, user_log, **kwargs):

    logger.debug("Log modified user id: {} :: user_log = {} :: user_log_time = {}.".format(
        user_log.user_id.user_id, user_log.log, user_log.log_time))

    user_log = {
        "user_id" : user_log.user_id.user_id,
        "log" : user_log.log,
        "log_time" : user_log.log_time,
    }

    channel = channels()
    async_to_sync(channel.send)(
        {
            'type': 'user_log',
            'user_log': user_log
        }
    )
