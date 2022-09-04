from django.apps import AppConfig


class RoomConfig(AppConfig):
    name = 'room'

    def ready(self):
        from . import updater
        updater.start()