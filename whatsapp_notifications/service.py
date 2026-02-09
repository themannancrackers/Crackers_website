"""
WhatsApp Notification Service
High-level functions to send order notifications
"""

import logging
from typing import Dict, Optional
from django.conf import settings
from .whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)


def format_order_items(order) -> str:
    """
    Format order items as a readable string.
    
    Args:
        order: Order instance with related items
        
    Returns:
        Formatted string of items (e.g., "Item1 x2, Item2 x1")
    """
    items = order.items.select_related('product').all()
    
    if not items:
        return "No items"
    
    item_list = []
    for item in items:
        item_list.append(f"{item.product.name} x{item.quantity}")
    
    return ", ".join(item_list)


def send_order_confirmation_to_customer(order) -> Dict:
    """
    Send order confirmation message to customer.
    
    Args:
        order: Order instance
        
    Returns:
        Dictionary with send result (success, message_id, etc.)
    """
    client = WhatsAppClient()
    
    # Format the message
    items = format_order_items(order)
    message_body = (
        f"🎉 Your order #{order.id} is confirmed!\n\n"
        f"Items: {items}\n"
        f"Total: ₹{order.total_amount:.2f}\n\n"
        f"We will update you on the delivery status soon.\n"
        f"Thank you for shopping with The Mannan Crackers!"
    )
    
    # Get customer phone number with international format
    phone_number = order.phone
    if not phone_number.startswith("+"):
        # Assuming Indian phone numbers, add +91 prefix
        phone_number = f"+91{phone_number}" if len(phone_number) == 10 else f"+{phone_number}"
    
    logger.info(f"Sending order confirmation to customer {order.full_name} ({phone_number})")
    
    result = client.send_text(phone_number, message_body)
    result['order_id'] = order.id
    result['recipient_type'] = 'customer'
    
    return result


def send_order_notification_to_admin(order) -> Dict:
    """
    Send new order notification to admin.
    
    Args:
        order: Order instance
        
    Returns:
        Dictionary with send result (success, message_id, etc.)
    """
    client = WhatsAppClient()
    admin_phone = getattr(settings, 'WHATSAPP_ADMIN_NUMBER', None)
    
    if not admin_phone:
        logger.warning(
            "WHATSAPP_ADMIN_NUMBER not configured. "
            "Skipping admin notification."
        )
        return {
            "success": False,
            "error": "Admin phone number not configured",
            "order_id": order.id,
            "recipient_type": "admin"
        }
    
    # Format the message
    items = format_order_items(order)
    message_body = (
        f"📦 New Order Received!\n\n"
        f"Order ID: #{order.id}\n"
        f"Customer: {order.full_name}\n"
        f"Phone: {order.phone}\n"
        f"Email: {order.email}\n\n"
        f"Items: {items}\n"
        f"Total: ₹{order.total_amount:.2f}\n\n"
        f"Delivery Address:\n{order.address}"
    )
    
    # Ensure admin phone has international format
    if not admin_phone.startswith("+"):
        admin_phone = f"+91{admin_phone}" if len(admin_phone) == 10 else f"+{admin_phone}"
    
    logger.info(f"Sending order notification to admin ({admin_phone})")
    
    result = client.send_text(admin_phone, message_body)
    result['order_id'] = order.id
    result['recipient_type'] = 'admin'
    
    return result


def send_order_notifications(order) -> Dict:
    """
    Send order notifications to both customer and admin.
    
    Main entry point for triggering WhatsApp notifications.
    Should be called after order is successfully created.
    
    Args:
        order: Order instance
        
    Returns:
        Dictionary with results for both customer and admin notifications
        {
            "customer": {...},
            "admin": {...},
            "order_id": <id>
        }
    """
    if not order.id:
        logger.error("Cannot send notifications for unsaved order")
        return {"error": "Order not saved", "order_id": None}
    
    logger.info(f"Initiating WhatsApp notifications for order #{order.id}")
    
    results = {
        "order_id": order.id,
        "timestamp": str(__import__('django.utils.timezone', fromlist=['now']).now()),
        "customer": {},
        "admin": {}
    }
    
    # Send to customer
    try:
        results["customer"] = send_order_confirmation_to_customer(order)
    except Exception as e:
        logger.error(f"Error sending customer notification: {str(e)}", exc_info=True)
        results["customer"] = {
            "success": False,
            "error": f"Exception: {str(e)}",
            "order_id": order.id,
            "recipient_type": "customer"
        }
    
    # Send to admin
    try:
        results["admin"] = send_order_notification_to_admin(order)
    except Exception as e:
        logger.error(f"Error sending admin notification: {str(e)}", exc_info=True)
        results["admin"] = {
            "success": False,
            "error": f"Exception: {str(e)}",
            "order_id": order.id,
            "recipient_type": "admin"
        }
    
    # Log summary
    customer_success = results["customer"].get("success", False)
    admin_success = results["admin"].get("success", False)
    
    if customer_success and admin_success:
        logger.info(f"✅ Both notifications sent successfully for order #{order.id}")
    elif customer_success or admin_success:
        logger.warning(
            f"⚠️  Partial notification success for order #{order.id} "
            f"(Customer: {customer_success}, Admin: {admin_success})"
        )
    else:
        logger.error(f"❌ Failed to send notifications for order #{order.id}")
    
    return results


def send_order_status_update(order, new_status: str) -> Dict:
    """
    Send order status update to customer.
    
    Optional function for notifying customer of status changes.
    Can be called manually or from a signal when order.status changes.
    
    Args:
        order: Order instance
        new_status: New order status (e.g., 'processing', 'shipped', 'delivered')
        
    Returns:
        Dictionary with send result
    """
    client = WhatsAppClient()
    
    status_messages = {
        'processing': '⚙️ Your order is being processed and will be shipped soon.',
        'shipped': '📦 Your order has been shipped! Track your package.',
        'delivered': '✅ Your order has been delivered successfully. Thank you!',
        'cancelled': '❌ Your order has been cancelled. Please contact support.',
    }
    
    status_message = status_messages.get(
        new_status,
        f'Your order status has been updated to: {new_status}'
    )
    
    message_body = (
        f"📬 Order Status Update\n\n"
        f"Order ID: #{order.id}\n"
        f"Status: {new_status.upper()}\n\n"
        f"{status_message}"
    )
    
    # Get customer phone number with international format
    phone_number = order.phone
    if not phone_number.startswith("+"):
        phone_number = f"+91{phone_number}" if len(phone_number) == 10 else f"+{phone_number}"
    
    logger.info(
        f"Sending status update '{new_status}' to customer "
        f"{order.full_name} ({phone_number})"
    )
    
    result = client.send_text(phone_number, message_body)
    result['order_id'] = order.id
    result['recipient_type'] = 'customer'
    result['update_type'] = 'status'
    
    return result
