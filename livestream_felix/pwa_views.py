from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import cache_control
from django.templatetags.static import static
from django.conf import settings
import json
import os


@cache_control(max_age=0)
def service_worker(request):
    """Serve the service worker from root scope"""
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'js', 'sw.js')
    try:
        with open(sw_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        content = '// Service worker not found'

    return HttpResponse(
        content,
        content_type='application/javascript',
        headers={
            'Service-Worker-Allowed': '/',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
        }
    )


def web_manifest(request):
    """Serve the web app manifest"""
    manifest = {
        "name": "LiveStream Felix",
        "short_name": "LSF",
        "description": "Professional Video Conferencing Platform",
        "start_url": "/dashboard/",
        "display": "standalone",
        "background_color": "#080c14",
        "theme_color": "#5b6ef5",
        "orientation": "any",
        "scope": "/",
        "icons": [
            {"src": request.build_absolute_uri(f"/static/icons/icon-{s}.png"),
             "sizes": f"{s}x{s}", "type": "image/png", "purpose": "any maskable"}
            for s in [72, 96, 128, 144, 152, 192, 384, 512]
        ],
        "shortcuts": [
            {"name": "New Meeting", "url": "/rooms/instant/",
             "icons": [{"src": request.build_absolute_uri("/static/icons/icon-96.png"), "sizes": "96x96"}]},
            {"name": "Join Meeting", "url": "/rooms/join/",
             "icons": [{"src": request.build_absolute_uri("/static/icons/icon-96.png"), "sizes": "96x96"}]},
        ],
        "prefer_related_applications": False,
    }
    return JsonResponse(manifest, headers={'Cache-Control': 'public, max-age=3600'})
