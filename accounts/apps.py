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
        
        # Auto-configure Google OAuth from environment variables
        self._setup_google_oauth()
    
    def _setup_google_oauth(self):
        """
        Automatically configure Google OAuth credentials from .env file.
        This ensures the SocialApplication is created in the database.
        """
        import os
        from django.contrib.sites.models import Site
        from allauth.socialaccount.models import SocialApp
        from django.db import connection
        from django.db.utils import OperationalError
        
        # Skip if database is not ready
        try:
            if not connection.ensure_connection():
                return
        except (OperationalError, Exception):
            return
        
        # Get credentials from environment
        google_client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
        google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
        
        # Only proceed if credentials are provided
        if not google_client_id or not google_client_secret:
            return
        
        try:
            # Get or create the current site
            site = Site.objects.get_current()
            
            # Check if Google OAuth app already exists with correct credentials
            try:
                google_app = SocialApp.objects.get(provider='google')
                
                # Update if credentials have changed
                if google_app.client_id != google_client_id or google_app.secret != google_client_secret:
                    google_app.client_id = google_client_id
                    google_app.secret = google_client_secret
                    google_app.save()
                    logger.info("✅ Google OAuth credentials updated from .env")
                
                # Ensure site is linked
                if not google_app.sites.filter(pk=site.pk).exists():
                    google_app.sites.add(site)
                    
            except SocialApp.DoesNotExist:
                # Create new Google OAuth app
                google_app = SocialApp.objects.create(
                    provider='google',
                    name='Google',
                    client_id=google_client_id,
                    secret=google_client_secret,
                )
                google_app.sites.add(site)
                logger.info("✅ Google OAuth credentials configured from .env")
                
        except Exception as e:
            # Silently fail - database might not be ready yet
            pass


