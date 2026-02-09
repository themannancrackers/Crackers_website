"""
Signal handlers for user authentication and OAuth integration.
Handles automatic role assignment and approval for OAuth users.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

CustomUser = get_user_model()


@receiver(post_save, sender=CustomUser)
def handle_user_post_save(sender, instance, created, **kwargs):
    """
    Handle post-save signal for user creation.
    Set default values if not already set.
    This runs for BOTH regular signup and OAuth signup.
    """
    if created:
        # Ensure new users have a default role if not set
        if not instance.role or instance.role == '':
            instance.role = 'customer'
            instance.save(update_fields=['role'])
        
        # Auto-approve if role is admin
        if instance.role == 'admin' and not instance.is_approved:
            instance.is_approved = True
            instance.save(update_fields=['is_approved'])
