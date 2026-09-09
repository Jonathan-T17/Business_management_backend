from django.apps import AppConfig


class WorkflowsConfig(AppConfig):
    name = "workflows"

    def ready(self):
        from .register_adapters import register_workflow_adapters
        register_workflow_adapters()
