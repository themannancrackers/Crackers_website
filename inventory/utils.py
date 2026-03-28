from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from decimal import Decimal

def format_currency(amount):
    """Format amount as currency"""
    return f"₹{Decimal(amount):.2f}"

import logging
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

def send_order_confirmation(order):
    """Send order confirmation email to customer using Order object."""
    try:
        subject = f'Order Confirmation - The Mannan Crackers [ORD-{order.id:06d}]'
        
        # Validate required fields on Order object
        if not order.email:
            raise ValidationError("Missing required customer email")
        if '@' not in order.email:
            raise ValidationError("Invalid email format")
            
        # Calculate order total and format cart items
        order_items = order.items.select_related('product').all()
        items_html = ""
        
        for item in order_items:
            item_price = Decimal(str(item.price))
            item_quantity = Decimal(str(item.quantity))
            item_total = item_price * item_quantity
            items_html += f"""
                <tr>
                    <td>{item.product.name}</td>
                    <td>{item_quantity}</td>
                    <td>{format_currency(item_price)}</td>
                    <td>{format_currency(item_total)}</td>
                </tr>
            """
            
        # Prepare email context
        context = {
            'customer_name': order.full_name,
            'order_total': format_currency(order.total_amount),
            'items_html': items_html,
            'delivery_address': order.address,
            'phone': order.phone,
            'email': order.email,
            'order_number': f'ORD-{order.id:06d}',
            # Only used in some templates if they iterate over cart_items, else items_html is used
            'cart_items': [{'name': i.product.name, 'quantity': i.quantity, 'price': i.price} for i in order_items]
        }

        # Render email templates
        try:
            html_message = render_to_string('inventory/email/order_confirmation.html', context)
            plain_message = render_to_string('inventory/email/order_confirmation.txt', context)
        except Exception as template_error:
            logger.warning(f"Failed to render email templates: {str(template_error)}. Sending plain text only.")
            html_message = None
            plain_message = f"Order Confirmation\n\nThank you for your order!\n\nOrder Total: {context['order_total']}\nDelivery Address: {context['delivery_address']}"

        # Send email with error handling
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.email],
                html_message=html_message,
                fail_silently=False
            )
            logger.info(f"✅ Order confirmation email sent successfully to {order.email}")
            return True
            
        except Exception as smtp_error:
            # Log the error but don't fail the order - email sending is non-critical
            error_msg = str(smtp_error)
            logger.warning(f"⚠️ Failed to send order confirmation email to {order.email}: {error_msg}")
            
            # Return True anyway so checkout completes - email is not critical
            return True
            
    except ValidationError as e:
        logger.error(f"❌ Validation error in order confirmation email: {str(e)}")
        # Don't re-raise - let checkout complete even if validation fails
        return False
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in order confirmation email: {str(e)}")
        # Don't re-raise - let checkout complete
        return False



def send_batch_stock_alerts(products=None):
    """
    Send a consolidated low stock alert email with all low stock items to admin.
    
    Args:
        products: Optional list of Product objects to check. If None, fetches all low stock products.
        
    Returns:
        Boolean indicating success or failure
    """
    try:
        from inventory.models import Product
        
        # Get all low stock products if not provided
        if products is None:
            products = Product.objects.filter(stock_quantity__lt=10)
        else:
            # Filter to only low stock products
            products = [p for p in products if p.stock_quantity < 10]
        
        if not products:
            logger.info("✅ No low stock products found - no alert needed")
            return True
        
        subject = f'Low Stock Alert - {len(products)} Item(s) Below Threshold'
        
        # Prepare product data for email template
        low_stock_items = []
        for product in products:
            low_stock_items.append({
                'id': product.id,
                'name': product.name,
                'category': product.category.name,
                'current_stock': product.stock_quantity,
                'threshold': 10,
                'shortage': 10 - product.stock_quantity
            })
        
        from django.utils import timezone
        context = {
            'total_items': len(low_stock_items),
            'items': low_stock_items,
            'timestamp': timezone.now()
        }

        # Render email templates with error handling
        try:
            html_message = render_to_string('inventory/email/batch_stock_alert.html', context)
            plain_message = render_to_string('inventory/email/batch_stock_alert.txt', context)
        except Exception as template_error:
            logger.warning(f"Failed to render batch stock alert templates: {str(template_error)}")
            html_message = None
            # Create plain text fallback
            plain_message = f"Low Stock Alert\n\nTotal Low Stock Items: {len(low_stock_items)}\n\n"
            plain_message += "Product\t\t\t\tCategory\t\tCurrent Stock\n"
            plain_message += "-" * 80 + "\n"
            for item in low_stock_items:
                plain_message += f"{item['name']}\t\t{item['category']}\t\t{item['current_stock']}\n"

        # Send email with error handling
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.EMAIL_HOST_USER],  # Send to admin email
                html_message=html_message,
                fail_silently=False
            )
            logger.info(f"✅ Batch stock alert email sent for {len(low_stock_items)} low stock items")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Failed to send batch stock alert email: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Unexpected error in batch stock alert email: {str(e)}")
        return False


# =====================================================
# 🔴 ERROR RESPONSE HANDLERS
# =====================================================

from django.http import JsonResponse

def handle_api_error(error_type, message, status_code=400, extra_data=None):
    """
    Generate standardized API error response
    
    error_type: 'validation', 'authentication', 'permission', 'not_found', 'server', 'network'
    message: Error message to display to user
    status_code: HTTP status code
    extra_data: Additional data to include in response
    """
    response_data = {
        'success': False,
        'error': message,
        'error_type': error_type,
        'error_code': status_code,
    }
    
    if extra_data:
        response_data.update(extra_data)
    
    logger.error(f"API Error [{error_type}]: {message}")
    return JsonResponse(response_data, status=status_code)


def get_error_message(error_type):
    """Get user-friendly error message based on error type"""
    messages = {
        'validation': 'The data you provided is invalid. Please check and try again.',
        'authentication': 'You need to log in to perform this action.',
        'permission': 'You don\'t have permission to perform this action.',
        'not_found': 'The requested resource was not found.',
        'server': 'An unexpected error occurred on our servers. Please try again later.',
        'network': 'Network connection error. Please check your internet and try again.',
        'checkout': 'An error occurred during checkout. Please review your information and try again.',
        'payment': 'Payment processing failed. Please try again or contact support.',
        'stock': 'Some items in your cart are no longer available. Please review your order.',
        'minimum_order': 'Minimum order amount not met. Please add more items to your cart.',
    }
    return messages.get(error_type, 'An unexpected error occurred. Please try again.')
