from channels.generic.websocket import WebsocketConsumer

class InfoConsumer(WebsocketConsumer):
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