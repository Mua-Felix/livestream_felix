from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rooms.models import Room, Participant
from accounts.models import User


@login_required
def home(request):
    user = request.user
    upcoming = Room.objects.filter(
        host=user, room_type='scheduled', status='waiting',
        scheduled_start__gte=timezone.now()
    ).order_by('scheduled_start')[:5]

    recent = Room.objects.filter(
        participants__user=user, status='ended'
    ).order_by('-ended_at').distinct()[:10]

    active_rooms = Room.objects.filter(
        participants__user=user, status='active'
    ).distinct()

    # Stats
    total_meetings = Participant.objects.filter(user=user).count()
    total_hosted = Room.objects.filter(host=user).count()
    total_minutes = user.total_minutes

    hour = timezone.localtime(timezone.now()).hour
    if hour < 12:
        greeting = 'morning'
    elif hour < 17:
        greeting = 'afternoon'
    else:
        greeting = 'evening'

    context = {
        'upcoming': upcoming,
        'recent': recent,
        'active_rooms': active_rooms,
        'total_meetings': total_meetings,
        'total_hosted': total_hosted,
        'total_minutes': total_minutes,
        'online_users': User.objects.filter(is_online=True).exclude(id=user.id)[:8],
        'time_greeting': greeting,
    }
    return render(request, 'dashboard/home.html', context)


@login_required
def meetings(request):
    filter_type = request.GET.get('filter', 'all')
    user = request.user

    if filter_type == 'hosted':
        rooms = Room.objects.filter(host=user)
    elif filter_type == 'joined':
        rooms = Room.objects.filter(participants__user=user).exclude(host=user)
    elif filter_type == 'upcoming':
        rooms = Room.objects.filter(host=user, status='waiting', scheduled_start__gte=timezone.now())
    else:
        rooms = Room.objects.filter(participants__user=user).distinct()

    rooms = rooms.order_by('-created_at')[:50]
    filter_options = [
        ('All', 'all'), ('Hosted', 'hosted'),
        ('Joined', 'joined'), ('Upcoming', 'upcoming'),
    ]
    return render(request, 'dashboard/meetings.html', {
        'rooms': rooms,
        'filter_type': filter_type,
        'filter_options': filter_options,
    })


@login_required
def people(request):
    users = User.objects.exclude(id=request.user.id).order_by('-is_online', 'first_name')[:50]
    return render(request, 'dashboard/people.html', {'users': users})
