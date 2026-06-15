from django.db import models
from django.conf import settings
import uuid
import random
import string


def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))


class Room(models.Model):
    ROOM_TYPES = [
        ('instant', 'Instant Meeting'),
        ('scheduled', 'Scheduled Meeting'),
        ('personal', 'Personal Room'),
        ('webinar', 'Webinar'),
    ]
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('active', 'Active'),
        ('ended', 'Ended'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True, default=generate_room_code)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='instant')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_rooms')
    password = models.CharField(max_length=50, blank=True)
    max_participants = models.PositiveIntegerField(default=100)
    is_recording = models.BooleanField(default=False)
    enable_waiting_room = models.BooleanField(default=False)
    mute_on_entry = models.BooleanField(default=False)
    allow_screen_share = models.BooleanField(default=True)
    allow_chat = models.BooleanField(default=True)
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.code})"

    @property
    def duration_minutes(self):
        if self.started_at and self.ended_at:
            return int((self.ended_at - self.started_at).total_seconds() / 60)
        return 0

    @property
    def participant_count(self):
        return self.participants.filter(left_at__isnull=True).count()


class Participant(models.Model):
    ROLE_CHOICES = [
        ('host', 'Host'),
        ('co_host', 'Co-Host'),
        ('panelist', 'Panelist'),
        ('attendee', 'Attendee'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='participations')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='attendee')
    is_muted = models.BooleanField(default=False)
    is_video_off = models.BooleanField(default=False)
    is_screen_sharing = models.BooleanField(default=False)
    is_hand_raised = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('room', 'user')
        ordering = ['joined_at']

    def __str__(self):
        return f"{self.user} in {self.room}"


class Reaction(models.Model):
    REACTIONS = [
        ('👍', 'Thumbs Up'), ('👏', 'Clap'), ('❤️', 'Heart'),
        ('😂', 'Laugh'), ('😮', 'Wow'), ('🎉', 'Celebrate'),
        ('🔥', 'Fire'), ('✋', 'Hand'),
    ]
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=10, choices=REACTIONS)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Whiteboard(models.Model):
    room = models.OneToOneField(Room, on_delete=models.CASCADE, related_name='whiteboard')
    data = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)
