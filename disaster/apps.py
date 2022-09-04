from django.apps import AppConfig
from . import updater

class DiasterConfig(AppConfig):
    name = 'disaster'

    def ready(self):
        updater.start()
        updater.start_2()