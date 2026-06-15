from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
import json
from .models import Room, Participant
from .forms import RoomCreateForm


@login_required
def create_room(request):
    if request.method == 'POST':
        form = RoomCreateForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.host = request.user
            room.status = 'active'
            room.started_at = timezone.now()
            room.save()
            # Create host participant
            Participant.objects.create(room=room, user=request.user, role='host')
            return redirect('rooms:room', code=room.code)
    else:
        form = RoomCreateForm()
    settings_fields = [
        ('Enable Waiting Room', 'enable_waiting_room'),
        ('Mute Participants on Entry', 'mute_on_entry'),
        ('Allow Screen Sharing', 'allow_screen_share'),
        ('Allow In-Meeting Chat', 'allow_chat'),
    ]
    return render(request, 'rooms/create.html', {'form': form, 'settings_fields': settings_fields})


@login_required
def instant_meeting(request):
    """One-click instant meeting creation"""
    room = Room.objects.create(
        title=f"{request.user.first_name or request.user.username}'s Meeting",
        host=request.user,
        status='active',
        started_at=timezone.now(),
        room_type='instant',
    )
    Participant.objects.create(room=room, user=request.user, role='host')
    return redirect('rooms:room', code=room.code)


@login_required
def join_room(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        password = request.POST.get('password', '')
        try:
            room = Room.objects.get(code=code)
            if room.password and room.password != password:
                return render(request, 'rooms/join.html', {'error': 'Incorrect password'})
            if room.status == 'ended':
                return render(request, 'rooms/join.html', {'error': 'This meeting has ended'})
            # Add participant if not already in
            Participant.objects.get_or_create(
                room=room, user=request.user,
                defaults={'role': 'host' if room.host == request.user else 'attendee'}
            )
            return redirect('rooms:room', code=room.code)
        except Room.DoesNotExist:
            return render(request, 'rooms/join.html', {'error': 'Room not found'})
    return render(request, 'rooms/join.html')


@login_required
def room_view(request, code):
    room = get_object_or_404(Room, code=code)
    if room.status == 'ended':
        return redirect('dashboard:home')

    # Get or create participant
    participant, _ = Participant.objects.get_or_create(
        room=room, user=request.user,
        defaults={'role': 'host' if room.host == request.user else 'attendee'}
    )

    # Activate room if host joins
    if room.host == request.user and room.status == 'waiting':
        room.status = 'active'
        room.started_at = timezone.now()
        room.save()

    participants = room.participants.filter(left_at__isnull=True).select_related('user')

    context = {
        'room': room,
        'participant': participant,
        'participants': participants,
        'is_host': room.host == request.user,
        'user_json': json.dumps({
            'id': str(request.user.id),
            'name': request.user.get_full_name() or request.user.username,
            'initials': request.user.initials,
        }),
    }
    return render(request, 'rooms/room.html', context)


@login_required
@require_POST
def end_room(request, code):
    room = get_object_or_404(Room, code=code, host=request.user)
    room.status = 'ended'
    room.ended_at = timezone.now()
    room.save()
    # Update host stats
    request.user.total_meetings += 1
    request.user.total_minutes += room.duration_minutes
    request.user.save(update_fields=['total_meetings', 'total_minutes'])
    return JsonResponse({'status': 'ended'})


@login_required
def room_participants_api(request, code):
    room = get_object_or_404(Room, code=code)
    participants = room.participants.filter(left_at__isnull=True).select_related('user')
    data = [{
        'id': str(p.user.id),
        'name': p.user.get_full_name() or p.user.username,
        'initials': p.user.initials,
        'role': p.role,
        'is_muted': p.is_muted,
        'is_video_off': p.is_video_off,
    } for p in participants]
    return JsonResponse({'participants': data})
