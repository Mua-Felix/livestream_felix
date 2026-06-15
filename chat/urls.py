from django.urls import path
from . import views
app_name = 'chat'
urlpatterns = [
    path('<str:room_code>/messages/', views.get_messages, name='messages'),
]
