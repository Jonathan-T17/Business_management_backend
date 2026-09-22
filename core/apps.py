from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from . import schema  # noqa: F401
        from . import schema_contracts  # noqa: F401
