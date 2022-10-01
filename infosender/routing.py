from django.urls import re_path 
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/socket-server/<str:user_id>/', consumers.InfoConsumer.as_asgi())
]