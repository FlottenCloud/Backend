from django.apps import AppConfig
from . import updater

class RoomConfig(AppConfig):
    name = 'room'

    def ready(self):
        updater.start()
        updater.start_2()