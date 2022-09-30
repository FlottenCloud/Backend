from django.apps import AppConfig


class InfosenderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'infosender'

    def ready(self):
        import infosender.signals