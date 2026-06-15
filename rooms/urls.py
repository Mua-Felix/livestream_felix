from django.urls import path
from . import views

app_name = 'rooms'

urlpatterns = [
    path('create/', views.create_room, name='create'),
    path('instant/', views.instant_meeting, name='instant'),
    path('join/', views.join_room, name='join'),
    path('<str:code>/', views.room_view, name='room'),
    path('<str:code>/end/', views.end_room, name='end'),
    path('<str:code>/participants/', views.room_participants_api, name='participants_api'),
]
