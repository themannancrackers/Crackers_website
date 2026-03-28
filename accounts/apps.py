import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    
    def ready(self):
        """
        Import signal handlers when the app is ready.
        This ensures signals are registered when Django starts.
        """
        import accounts.signals  # noqa

