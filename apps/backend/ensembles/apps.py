from django.apps import AppConfig


class EnsemblesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ensembles'

    def ready(self):
        from ensembles.lib.fonts import register_fonts
        register_fonts()
