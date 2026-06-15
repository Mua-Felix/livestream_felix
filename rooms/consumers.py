import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'room_{self.room_code}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Notify others that user joined
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'user_joined',
            'user_id': str(self.user.id),
            'username': self.user.get_full_name() or self.user.username,
            'initials': self.user.initials,
            'channel_name': self.channel_name,
        })

    async def disconnect(self, close_code):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'user_left',
            'user_id': str(self.user.id),
            'username': self.user.get_full_name() or self.user.username,
        })
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.mark_participant_left()

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type')

        handlers = {
            'offer': self.handle_offer,
            'answer': self.handle_answer,
            'ice_candidate': self.handle_ice_candidate,
            'toggle_mic': self.handle_toggle_mic,
            'toggle_video': self.handle_toggle_video,
            'screen_share': self.handle_screen_share,
            'raise_hand': self.handle_raise_hand,
            'reaction': self.handle_reaction,
            'kick_user': self.handle_kick_user,
            'mute_user': self.handle_mute_user,
            'end_meeting': self.handle_end_meeting,
            'whiteboard': self.handle_whiteboard,
            'poll': self.handle_poll,
            'breakout': self.handle_breakout,
        }

        handler = handlers.get(msg_type)
        if handler:
            await handler(data)

    # ── WebRTC Signaling ──────────────────────────────────────────────
    async def handle_offer(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'webrtc_offer',
            'offer': data['offer'],
            'sender_id': str(self.user.id),
            'target_id': data.get('target_id'),
        })

    async def handle_answer(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'webrtc_answer',
            'answer': data['answer'],
            'sender_id': str(self.user.id),
            'target_id': data.get('target_id'),
        })

    async def handle_ice_candidate(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'webrtc_ice',
            'candidate': data['candidate'],
            'sender_id': str(self.user.id),
            'target_id': data.get('target_id'),
        })

    # ── Media Controls ────────────────────────────────────────────────
    async def handle_toggle_mic(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'media_update',
            'user_id': str(self.user.id),
            'mic': data.get('enabled'),
            'video': None,
        })

    async def handle_toggle_video(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'media_update',
            'user_id': str(self.user.id),
            'mic': None,
            'video': data.get('enabled'),
        })

    async def handle_screen_share(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'screen_share_update',
            'user_id': str(self.user.id),
            'username': self.user.get_full_name() or self.user.username,
            'sharing': data.get('sharing'),
        })

    async def handle_raise_hand(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'hand_raised',
            'user_id': str(self.user.id),
            'username': self.user.get_full_name() or self.user.username,
            'raised': data.get('raised'),
        })

    async def handle_reaction(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'reaction_sent',
            'user_id': str(self.user.id),
            'username': self.user.get_full_name() or self.user.username,
            'emoji': data.get('emoji'),
        })

    # ── Host Controls ─────────────────────────────────────────────────
    async def handle_kick_user(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'user_kicked',
            'target_id': data.get('target_id'),
            'host_id': str(self.user.id),
        })

    async def handle_mute_user(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'force_mute',
            'target_id': data.get('target_id'),
        })

    async def handle_end_meeting(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'meeting_ended',
            'host_id': str(self.user.id),
        })

    async def handle_whiteboard(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'whiteboard_update',
            'data': data.get('data'),
            'user_id': str(self.user.id),
        })

    async def handle_poll(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'poll_update',
            'poll': data.get('poll'),
            'user_id': str(self.user.id),
        })

    async def handle_breakout(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'breakout_update',
            'rooms': data.get('rooms'),
            'user_id': str(self.user.id),
        })

    # ── Group message handlers ────────────────────────────────────────
    async def user_joined(self, event):
        await self.send(text_data=json.dumps({'type': 'user_joined', **event}))

    async def user_left(self, event):
        await self.send(text_data=json.dumps({'type': 'user_left', **event}))

    async def webrtc_offer(self, event):
        await self.send(text_data=json.dumps({'type': 'offer', **event}))

    async def webrtc_answer(self, event):
        await self.send(text_data=json.dumps({'type': 'answer', **event}))

    async def webrtc_ice(self, event):
        await self.send(text_data=json.dumps({'type': 'ice_candidate', **event}))

    async def media_update(self, event):
        await self.send(text_data=json.dumps({'type': 'media_update', **event}))

    async def screen_share_update(self, event):
        await self.send(text_data=json.dumps({'type': 'screen_share', **event}))

    async def hand_raised(self, event):
        await self.send(text_data=json.dumps({'type': 'hand_raised', **event}))

    async def reaction_sent(self, event):
        await self.send(text_data=json.dumps({'type': 'reaction', **event}))

    async def user_kicked(self, event):
        await self.send(text_data=json.dumps({'type': 'kicked', **event}))

    async def force_mute(self, event):
        await self.send(text_data=json.dumps({'type': 'force_mute', **event}))

    async def meeting_ended(self, event):
        await self.send(text_data=json.dumps({'type': 'meeting_ended', **event}))

    async def whiteboard_update(self, event):
        await self.send(text_data=json.dumps({'type': 'whiteboard', **event}))

    async def poll_update(self, event):
        await self.send(text_data=json.dumps({'type': 'poll', **event}))

    async def breakout_update(self, event):
        await self.send(text_data=json.dumps({'type': 'breakout', **event}))

    @database_sync_to_async
    def mark_participant_left(self):
        from .models import Participant
        Participant.objects.filter(
            room__code=self.room_code,
            user=self.user,
            left_at__isnull=True
        ).update(left_at=timezone.now())
