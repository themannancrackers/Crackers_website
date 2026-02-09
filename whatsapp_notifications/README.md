"""
WhatsApp Notifications Integration Guide
Django e-commerce WhatsApp Cloud API Integration
"""

# =====================================================
# 1. INSTALLATION & SETUP
# =====================================================

"""
Step 1: Add to INSTALLED_APPS in settings.py
    INSTALLED_APPS = [
        ...
        'whatsapp_notifications',
    ]

Step 2: Add WhatsApp configuration to settings.py (see SETTINGS_CONFIG below)

Step 3: Migrate (if using Django models, currently only using signals)
    python manage.py makemigrations
    python manage.py migrate

Step 4: Install requests library (if not already installed)
    pip install requests

Step 5: Test the integration
    python manage.py test whatsapp_notifications
"""

# =====================================================
# 2. DJANGO SETTINGS CONFIGURATION
# =====================================================

"""
Add the following to your Django settings.py:

# WhatsApp Cloud API Configuration
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID', '')
WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN', '')
WHATSAPP_API_VERSION = os.getenv('WHATSAPP_API_VERSION', 'v18.0')
WHATSAPP_ADMIN_NUMBER = os.getenv('WHATSAPP_ADMIN_NUMBER', '')

# Dry-run mode (set to False for production)
# When True: logs messages without making API calls
# When False: sends actual WhatsApp messages via Meta API
WHATSAPP_DRY_RUN = os.getenv('WHATSAPP_DRY_RUN', 'True') == 'True'

# Enable/disable WhatsApp notifications globally
WHATSAPP_NOTIFICATIONS_ENABLED = os.getenv('WHATSAPP_NOTIFICATIONS_ENABLED', 'True') == 'True'

Example .env file:
    WHATSAPP_PHONE_NUMBER_ID=1234567890123456
    WHATSAPP_ACCESS_TOKEN=EAABs...YOUR_TOKEN_HERE
    WHATSAPP_API_VERSION=v18.0
    WHATSAPP_ADMIN_NUMBER=+919876543210
    WHATSAPP_DRY_RUN=True  # Set to False in production
    WHATSAPP_NOTIFICATIONS_ENABLED=True
"""

# =====================================================
# 3. USAGE EXAMPLES
# =====================================================

# Option A: Automatic (via Django Signal)
# =====================================================
"""
The notification is sent AUTOMATICALLY when an order is created.

How it works:
    1. User places order and Order object is saved to database
    2. Django's post_save signal is triggered (in signals.py)
    3. send_order_notifications() is called automatically
    4. Messages sent to customer and admin

Location: whatsapp_notifications/signals.py

Control: Set WHATSAPP_NOTIFICATIONS_ENABLED=False to disable
"""

# Option B: Manual (in View)
# =====================================================
"""
If you want to send notifications manually from your checkout view:

from whatsapp_notifications.service import send_order_notifications

# Inside checkout view after order is created:
@require_http_methods(["GET", "POST"])
@login_required(login_url='account_login')
def checkout(request):
    if request.method == 'POST':
        # ... existing checkout logic ...
        
        # Create order
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            full_name=customer_data['fullName'],
            address=customer_data['deliveryAddress'],
            phone=customer_data['phone'],
            email=customer_data['email'],
            total_amount=total_amount,
            status='pending'
        )
        
        # Create order items
        for product_id, item in cart_items.items():
            OrderItem.objects.create(...)
        
        # Send WhatsApp notifications
        notification_results = send_order_notifications(order)
        logger.info(f"WhatsApp notifications sent: {notification_results}")
        
        return JsonResponse({
            'success': True,
            'message': 'Order placed successfully!',
            'orderSummary': order_summary,
            'notifications_sent': notification_results  # Optional: include in response
        })
"""

# Option C: Manual (in Management Command)
# =====================================================
"""
For testing or manually sending notifications:

from whatsapp_notifications.service import send_order_notifications
from inventory.models import Order

order = Order.objects.get(id=123)
results = send_order_notifications(order)
print(results)
"""

# =====================================================
# 4. DRY-RUN OUTPUT EXAMPLE
# =====================================================

"""
When WHATSAPP_DRY_RUN=True, console output looks like:

[DRY RUN] WhatsApp message would be sent
To: +919876543210
Message: 🎉 Your order #123 is confirmed!

Items: Product A x2, Product B x1
Total: ₹5000.00

We will update you on the delivery status soon.
Thank you for shopping with The Mannan Crackers!

Full Payload: {
  "messaging_product": "whatsapp",
  "to": "+919876543210",
  "type": "text",
  "text": {
    "preview_url": false,
    "body": "🎉 Your order #123 is confirmed!..."
  }
}

[DRY RUN] WhatsApp message would be sent
To: +919999999999
Message: 📦 New Order Received!

Order ID: #123
Customer: John Doe
Phone: 9876543210
Email: john@example.com

Items: Product A x2, Product B x1
Total: ₹5000.00

Delivery Address:
123 Main Street, City, State 560001

Full Payload: {...}
"""

# =====================================================
# 5. PRODUCTION API PAYLOAD EXAMPLE
# =====================================================

"""
When WHATSAPP_DRY_RUN=False, the following JSON is sent to Meta's API:

POST https://graph.facebook.com/v18.0/1234567890123456/messages

Headers:
    Authorization: Bearer EAABs...YOUR_TOKEN_HERE
    Content-Type: application/json

Body (Customer Message):
{
  "messaging_product": "whatsapp",
  "to": "+919876543210",
  "type": "text",
  "text": {
    "preview_url": false,
    "body": "🎉 Your order #123 is confirmed!\\n\\nItems: Product A x2, Product B x1\\nTotal: ₹5000.00\\n\\nWe will update you on the delivery status soon.\\nThank you for shopping with The Mannan Crackers!"
  }
}

Meta API Response (Success):
{
  "messages": [
    {
      "id": "wamid.HBEUGBaBAApLAgkQ1234567890"
    }
  ],
  "contacts": [
    {
      "input": "+919876543210",
      "wa_id": "919876543210"
    }
  ]
}

Meta API Response (Error):
{
  "error": {
    "message": "Invalid phone number",
    "type": "OAuthException",
    "code": 400
  }
}
"""

# =====================================================
# 6. INTEGRATION POINTS
# =====================================================

"""
Option 1: Signal-based (Recommended for automatic flow)
Location: whatsapp_notifications/signals.py
Triggered: When Order.objects.create() is called
Requires: WHATSAPP_NOTIFICATIONS_ENABLED=True
Advantage: Automatic, no code changes needed in views
Disadvantage: Harder to debug if issues arise

Option 2: View-based (Recommended for manual control)
Location: inventory/views.py - checkout() function
Call: send_order_notifications(order) after order creation
Advantage: Full control, can handle errors gracefully
Disadvantage: Requires modifying existing code

Option 3: Celery Task (Recommended for production)
Location: Create whatsapp_notifications/tasks.py
Benefit: Async, doesn't block checkout flow
Not implemented in this version, but easy to add:

from celery import shared_task
from .service import send_order_notifications

@shared_task
def send_notifications_async(order_id):
    from inventory.models import Order
    order = Order.objects.get(id=order_id)
    return send_order_notifications(order)

Then in signal: send_notifications_async.delay(order.id)
"""

# =====================================================
# 7. PHONE NUMBER FORMATS
# =====================================================

"""
Supported formats (automatically normalized):
    ✅ +919876543210 (international)
    ✅ +91 9876543210 (with space)
    ✅ +91-9876543210 (with dash)
    ❌ 9876543210 (without country code) — auto-prefixed with +91
    ❌ 919876543210 (without + prefix) — auto-prefixed with +

The code automatically adds +91 for Indian numbers without country code.
For other countries, provide full international format with +
"""

# =====================================================
# 8. ERROR HANDLING & LOGGING
# =====================================================

"""
All errors are logged to Django logging system:
    logger = logging.getLogger(__name__)

Configure logging in settings.py:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'file': {
                'level': 'INFO',
                'class': 'logging.FileHandler',
                'filename': 'whatsapp_notifications.log',
            },
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            'whatsapp_notifications': {
                'handlers': ['file', 'console'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }

Log levels:
    DEBUG: Detailed request/response info
    INFO: Successful sends, dry-run details
    WARNING: Skipped notifications, partial failures
    ERROR: API errors, exceptions, failed sends
"""

# =====================================================
# 9. TESTING
# =====================================================

"""
Run all tests:
    python manage.py test whatsapp_notifications

Run specific test class:
    python manage.py test whatsapp_notifications.tests.WhatsAppClientTestCase

Run specific test:
    python manage.py test whatsapp_notifications.tests.WhatsAppClientTestCase.test_dry_run_mode_enabled

Run with verbose output:
    python manage.py test whatsapp_notifications -v 2

Test coverage (install coverage package):
    pip install coverage
    coverage run --source='whatsapp_notifications' manage.py test whatsapp_notifications
    coverage report
"""

# =====================================================
# 10. TROUBLESHOOTING
# =====================================================

"""
Issue: Messages not being sent
Solution:
    1. Check WHATSAPP_DRY_RUN is False for production
    2. Verify WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN are set
    3. Check logs for error messages
    4. Ensure customer phone number has international format

Issue: Invalid phone number error
Solution:
    1. Ensure phone number starts with +
    2. Provide country code (e.g., +91 for India)
    3. Remove any non-digit characters except +

Issue: Signal not triggered
Solution:
    1. Verify 'whatsapp_notifications' is in INSTALLED_APPS
    2. Check that apps.py has ready() method importing signals
    3. Ensure WHATSAPP_NOTIFICATIONS_ENABLED=True

Issue: API timeout
Solution:
    1. Check network connectivity
    2. Verify Meta API endpoint is accessible
    3. Consider implementing Celery for async sending

Issue: Missing admin phone number
Solution:
    1. Set WHATSAPP_ADMIN_NUMBER in settings.py or .env
    2. Admin notification will be skipped if not configured
    3. Check logs for warning messages
"""
