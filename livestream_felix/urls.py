from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from .pwa_views import service_worker, web_manifest

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda r: redirect('dashboard:home'), name='home'),
    path('sw.js', service_worker, name='service_worker'),
    path('manifest.json', web_manifest, name='manifest'),
    path('accounts/', include('accounts.urls')),
    path('rooms/', include('rooms.urls')),
    path('chat/', include('chat.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('billing/', include('billing.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
