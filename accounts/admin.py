from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_online', 'total_meetings')
    fieldsets = UserAdmin.fieldsets + (
        ('LiveStream Felix', {'fields': ('avatar', 'bio', 'job_title', 'organization', 'is_online', 'total_meetings', 'total_minutes')}),
    )
