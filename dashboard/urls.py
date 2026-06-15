from django.urls import path
from . import views
app_name = 'dashboard'
urlpatterns = [
    path('', views.home, name='home'),
    path('meetings/', views.meetings, name='meetings'),
    path('people/', views.people, name='people'),
]
