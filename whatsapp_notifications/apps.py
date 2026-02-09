"""
App configuration for WhatsApp Notifications
"""

from django.apps import AppConfig


class WhatsappNotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'whatsapp_notifications'
    verbose_name = 'WhatsApp Notifications'

    def ready(self):
        """
        Import signals when app is ready.
        This ensures post_save signals are registered for Order model.
        """
        import whatsapp_notifications.signals  # noqa: F401
