import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Import routing BEFORE creating Django application to avoid E402
from smartpark.routing import websocket_urlpatterns  # noqa: E402

# Create the default Django ASGI application
django_application = get_asgi_application()

# Wrap with WebSocket support
application = ProtocolTypeRouter(
    {
        "http": django_application,
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
