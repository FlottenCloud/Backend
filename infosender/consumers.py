import json

from channels.generic.websocket import AsyncWebsocketConsumer

class InfoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user_id = self.scope["url_route"]["kwargs"]["user_id"]
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