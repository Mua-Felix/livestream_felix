from django.db import models
from django.conf import settings
import uuid


class Message(models.Model):
    MSG_TYPES = [
        ('text', 'Text'),
        ('file', 'File'),
        ('image', 'Image'),
        ('system', 'System'),
        ('reaction', 'Reaction'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey('rooms.Room', on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages', null=True)
    msg_type = models.CharField(max_length=20, choices=MSG_TYPES, default='text')
    content = models.TextField()
    file = models.FileField(upload_to='chat_files/', null=True, blank=True)
    is_pinned = models.BooleanField(default=False)
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender}: {self.content[:50]}"


class DirectMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dm_sent')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dm_received')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
