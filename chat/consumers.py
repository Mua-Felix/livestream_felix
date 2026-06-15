import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'chat_{self.room_code}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Send chat history
        messages = await self.get_history()
        await self.send(text_data=json.dumps({'type': 'history', 'messages': messages}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'message')

        if msg_type == 'message':
            message = await self.save_message(data.get('content', ''), data.get('reply_to'))
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'chat_message',
                'id': str(message.id),
                'content': message.content,
                'sender_id': str(self.user.id),
                'sender_name': self.user.get_full_name() or self.user.username,
                'sender_initials': self.user.initials,
                'timestamp': message.created_at.strftime('%H:%M'),
                'reply_to': data.get('reply_to'),
            })
        elif msg_type == 'typing':
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'user_typing',
                'user_id': str(self.user.id),
                'username': self.user.get_full_name() or self.user.username,
                'is_typing': data.get('is_typing', False),
            })
        elif msg_type == 'pin':
            await self.pin_message(data.get('message_id'))
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'message_pinned',
                'message_id': data.get('message_id'),
            })

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({'type': 'message', **event}))

    async def user_typing(self, event):
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({'type': 'typing', **event}))

    async def message_pinned(self, event):
        await self.send(text_data=json.dumps({'type': 'pinned', **event}))

    @database_sync_to_async
    def save_message(self, content, reply_to_id=None):
        from .models import Message
        from rooms.models import Room
        room = Room.objects.get(code=self.room_code)
        reply_to = None
        if reply_to_id:
            try:
                reply_to = Message.objects.get(id=reply_to_id)
            except Message.DoesNotExist:
                pass
        return Message.objects.create(
            room=room,
            sender=self.user,
            content=content,
            reply_to=reply_to,
        )

    @database_sync_to_async
    def get_history(self):
        from .models import Message
        from rooms.models import Room
        try:
            room = Room.objects.get(code=self.room_code)
            messages = Message.objects.filter(room=room).select_related('sender').order_by('created_at')[:100]
            return [{
                'id': str(m.id),
                'content': m.content,
                'sender_id': str(m.sender.id) if m.sender else None,
                'sender_name': m.sender.get_full_name() or m.sender.username if m.sender else 'System',
                'sender_initials': m.sender.initials if m.sender else '?',
                'timestamp': m.created_at.strftime('%H:%M'),
                'is_pinned': m.is_pinned,
            } for m in messages]
        except Exception:
            return []

    @database_sync_to_async
    def pin_message(self, message_id):
        from .models import Message
        Message.objects.filter(id=message_id).update(is_pinned=True)
