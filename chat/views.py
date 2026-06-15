from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Message
from rooms.models import Room

@login_required
def get_messages(request, room_code):
    room = Room.objects.get(code=room_code)
    messages = Message.objects.filter(room=room).select_related('sender').order_by('created_at')[:100]
    data = [{
        'id': str(m.id),
        'content': m.content,
        'sender_name': m.sender.get_full_name() or m.sender.username if m.sender else 'System',
        'timestamp': m.created_at.strftime('%H:%M'),
    } for m in messages]
    return JsonResponse({'messages': data})
