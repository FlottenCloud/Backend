from django.apps import AppConfig


class OpenstackConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'openstack'

    # def ready(self):
        # from . import updater
        # updater.start()