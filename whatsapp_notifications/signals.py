"""
Django Signals for WhatsApp Notifications
Automatically trigger notifications when orders are created/updated
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from inventory.models import Order
from .service import send_order_notifications

logger = logging.getLogger(__name__)


# Control whether signals are enabled via settings
WHATSAPP_NOTIFICATIONS_ENABLED = getattr(
    settings,
    'WHATSAPP_NOTIFICATIONS_ENABLED',
    True
)


@receiver(post_save, sender=Order)
def send_order_notification_signal(sender, instance, created, **kwargs):
    """
    Signal handler to send WhatsApp notifications when a new order is created.
    
    This is called automatically by Django after Order.save()
    
    Args:
        sender: The model class (Order)
        instance: The Order instance being saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    if not WHATSAPP_NOTIFICATIONS_ENABLED:
        logger.debug("WhatsApp notifications disabled in settings")
        return
    
    # Only send notification for newly created orders
    if not created:
        logger.debug(f"Skipping notification for updated order #{instance.id}")
        return
    
    # Skip if order is in invalid state
    if not instance.id or not instance.phone or not instance.email:
        logger.warning(
            f"Skipping notification for order #{instance.id}: "
            f"Missing required fields"
        )
        return
    
    try:
        logger.info(f"Signal triggered: Sending notifications for new order #{instance.id}")
        results = send_order_notifications(instance)
        logger.info(f"Notification results for order #{instance.id}: {results}")
    except Exception as e:
        logger.error(
            f"Error in WhatsApp notification signal for order #{instance.id}: {str(e)}",
            exc_info=True
        )
        # Don't raise the exception — let the order save complete
        # even if notifications fail
