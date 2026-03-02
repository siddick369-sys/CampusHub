# stages/consumers.py

from channels.generic.websocket import AsyncWebsocketConsumer
import json

class CallConsumer(AsyncWebsocketConsumer):
    """
    Signaling WebRTC très simple :
    - /ws/call/<conversation_id>/
    - On relaye simplement: offer / answer / candidate / hangup
    """
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"call_{self.conversation_id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")
        payload  = data.get("data", {})

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "call.message",
                "payload": {
                    "type": msg_type,
                    "data": payload,
                }
            }
        )

    async def call_message(self, event):
        await self.send(text_data=json.dumps(event["payload"]))