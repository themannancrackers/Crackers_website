from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import io
import os
import base64
import logging
from django.core.exceptions import ValidationError
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)

def format_currency(amount):
    """Format amount as currency"""
    return f"₹{Decimal(amount):.2f}"

from PIL import Image, ImageDraw

def get_logo_base64():
    """Get base64 string of the circular company logo for embedding in PDF & printable HTML invoices."""
    try:
        # Search possible production paths for Mannan_logo (png, PNG, jpg, etc.)
        possible_paths = [
            os.path.join(settings.BASE_DIR, 'staticfiles', 'images', 'Mannan_logo.png'),
            os.path.join(settings.STATIC_ROOT or '', 'images', 'Mannan_logo.png'),
            os.path.join(settings.BASE_DIR, 'static', 'images', 'Mannan_logo.png'),
            os.path.join(settings.MEDIA_ROOT, 'profile_pictures', 'Mannan_logo.png'),
            os.path.join(settings.MEDIA_ROOT, 'profile_pictures', 'Mannan_logo.PNG'),
            os.path.join(settings.BASE_DIR, 'media', 'profile_pictures', 'Mannan_logo.png'),
            os.path.join(settings.BASE_DIR, 'static', 'images', 'kannan_logo.png'),
        ]
        
        logo_path = None
        for p in possible_paths:
            if p and os.path.exists(p):
                logo_path = p
                break
            
        if logo_path:
            with open(logo_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            ext = os.path.splitext(logo_path)[1].lower().replace('.', '')
            if ext == 'jpg': ext = 'jpeg'
            return f"data:image/{ext};base64,{encoded}"
        else:
            logger.warning(f"No valid logo file found in search paths: {possible_paths}")
    except Exception as e:
        logger.error(f"Error generating logo base64: {str(e)}", exc_info=True)
    return ""

def generate_order_pdf(order):
    """
    Generate PDF bytes and custom filename for an Order object.
    Filename format: 'Mannan Crackers YYYY-MM-DD.pdf'
    """
    try:
        items = order.items.select_related('product').all()
        today_date = timezone.now()
        date_str = today_date.strftime('%Y-%m-%d')
        filename = f"Mannan Crackers {date_str}.pdf"

        formatted_items = []
        for item in items:
            price = Decimal(str(item.price))
            qty = Decimal(str(item.quantity))
            total = price * qty
            formatted_items.append({
                'product': item.product,
                'quantity': item.quantity,
                'price': price,
                'total': total
            })

        context = {
            'order': order,
            'items': formatted_items,
            'today_date': today_date,
            'logo_base64': get_logo_base64(),
        }

        html_content = render_to_string('inventory/invoice_pdf.html', context)
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)

        if pisa_status.err:
            logger.error(f"Error rendering PDF for Order #{order.id}: {pisa_status.err}")
            return None, filename

        return pdf_buffer.getvalue(), filename
    except Exception as e:
        logger.error(f"Failed to generate order PDF: {str(e)}")
        return None, f"Mannan Crackers {timezone.now().strftime('%Y-%m-%d')}.pdf"

def send_order_confirmation(order):
    """Send order confirmation email to customer using Order object, with attached PDF bill."""
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

        # Send email with PDF attachment
        try:
            email_msg = EmailMessage(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[order.email],
            )
            if html_message:
                email_msg.attach_alternative(html_message, "text/html")
            
            # Attach PDF bill: "Mannan Crackers YYYY-MM-DD.pdf"
            pdf_bytes, pdf_filename = generate_order_pdf(order)
            if pdf_bytes:
                email_msg.attach(pdf_filename, pdf_bytes, "application/pdf")
                
            email_msg.send(fail_silently=False)
            logger.info(f"✅ Order confirmation email with PDF attached sent successfully to {order.email}")
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


