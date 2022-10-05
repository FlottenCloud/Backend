import json

from channels.generic.websocket import AsyncWebsocketConsumer

class InfoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            user_id = self.scope["user"]
            print(user_id)
        except:
            user_id = "AnonymousUser"
        print(user_id)
        self.group_name = "user-{}".format(user_id)
        print(self.group_name)

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name            
        )
        await self.accept()

        await self.send(text_data=json.dumps({
            "type" : "connection_established",
            "message" : "Connected to 뜬구름"
        }))

    async def disconnect(self, code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def user_log_send(self, event):
        message = event["message"]

        await self.send(text_data=json.dumps({
            "type" : "user_log",
            "message" : message
        }))

    async def instance_log_send(self, event):
        message = event["message"]

        await self.send(text_data=json.dumps({
            "type" : "instance_log",
            "message" : message
        }))

    async def server_log_send(self, event):
        message = event["message"]

        await self.send(text_data=json.dumps({
            "type" : "server_log",
            "message" : message
        }))