import json
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import AccountInfo


class UserLogConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user_id = self.scope["user"]

        await self.accept()
        await self.sendUserLog(user_id)

    async def disconnect(self, close_code):
        await self.discard(
            self.channel_name
        )

    async def sendUserLog(self, user_id):
        user_id = AccountInfo.objects.filter(pk=user_id)
        user_logs = user_id.user_log.order_by('-log_time')

        for log in user_logs:
            user_log = {
                "user_id" : log.user_id.user_id,
                "log" : log.log,
                "log_time" : log.log_time
            }

            await self.send(
                self.channel_name,
                {
                    "type": "user_log",
                    "user_log": user_log
                }
            )


# class UserConsumer(AsyncWebsocketConsumer):   # 얘는 오픈스택 앱으로 빠져야할 것 같다는 생각. 일단 주석처리
#     async def connect(self):
#         user = self.scope["user"]
#         await self.accept()
#         await self.sendOpenstackInstanceChange(user)

#     async def disconnect(self, close_code):
#         await self.discard(
#             self.channel_name
#         )

#     async def sendOpenstackInstanceChange(self, user):
#         changed_instance = user.user_resource_info.order_by('-instance_pk')  # instance의 pk 순으로 정렬한 query set

#         for instance in changed_instance:
#             changed_instance_info = {
#                 "user_id" : instance.user_id.user_id,
#                 "instance_pk" : instance.instance_pk,
#                 "instance_id" : instance.instance_id,
#                 "instance_name" : instance.instance_name,
#                 "stack_id" : instance.stack_id,
#                 "stack_name" : instance.stack_name,
#                 "ip_address" : instance.ip_address,
#                 "status" : instance.status,
#                 "image_name" : instance.image_name,
#                 "os" : instance.os,
#                 "flavor_name" : instance.flavor_name,
#                 "ram_size" : instance.ram_size,
#                 "num_people" : instance.num_people,
#                 "expected_data_size" : instance.expected_data_size,
#                 "disk_size" : instance.disk_size,
#                 "num_cpu" : instance.num_cpu,
#                 "package" : instance.package,
#                 "backup_time" : instance.backup_time,
#                 "update_image_ID" : instance.update_image_ID,
#                 "freezer_completed" : instance.freezer_completed
#             }
#             await self.send(
#                 self.channel_name,
#                 {
#                     "type" : "changed_instance_info",
#                     "instance_type" : "openstack",
#                     "changed_instance_info" : changed_instance_info
#                 }
#             )