from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=300, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    organization = models.CharField(max_length=150, blank=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    total_meetings = models.PositiveIntegerField(default=0)
    total_minutes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return None

    @property
    def initials(self):
        parts = (self.get_full_name() or self.username).split()
        return ''.join(p[0].upper() for p in parts[:2])
