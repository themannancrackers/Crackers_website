"""
Management command to test WhatsApp integration
Tests both dry-run and actual message sending
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from whatsapp_notifications.whatsapp_client import WhatsAppClient
from whatsapp_notifications.service import send_order_notifications
from whatsapp_notifications.simulator import WhatsAppMessageSimulator
from inventory.models import Order
import json


class Command(BaseCommand):
    help = 'Test WhatsApp integration with dry-run or actual message sending'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            default=None,
            help='Phone number to send test message to (e.g., +918074101457)'
        )
        parser.add_argument(
            '--order',
            type=int,
            default=None,
            help='Order ID to test with (sends actual order notification)'
        )
        parser.add_argument(
            '--mode',
            type=str,
            choices=['dry-run', 'production'],
            default='dry-run',
            help='Test mode: dry-run (logs only) or production (actual API call)'
        )
        parser.add_argument(
            '--message',
            type=str,
            default='Hello! This is a test message from WhatsApp Cloud API integration.',
            help='Custom test message'
        )
        parser.add_argument(
            '--simulate',
            action='store_true',
            help='Simulate receiving a WhatsApp message (no sending)'
        )
        parser.add_argument(
            '--raw-json',
            action='store_true',
            help='Show raw JSON payload in simulation mode'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('WhatsApp Integration Test Tool'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))

        # Display current settings
        self._display_settings()

        # Simulation mode (no actual sending)
        if options['simulate']:
            self._test_simulation(options)
            return

        # Get test mode
        mode = options['mode']
        if mode == 'production':
            self._confirm_production_mode()

        # Run appropriate test
        if options['order']:
            self._test_with_order(options['order'])
        elif options['phone']:
            self._test_with_phone(options['phone'], options['message'])
        else:
            self._show_usage()

    def _display_settings(self):
        """Display current WhatsApp configuration"""
        self.stdout.write(self.style.WARNING('Current Configuration:'))
        self.stdout.write(f"  DRY_RUN: {settings.WHATSAPP_DRY_RUN}")
        self.stdout.write(f"  NOTIFICATIONS_ENABLED: {settings.WHATSAPP_NOTIFICATIONS_ENABLED}")
        self.stdout.write(f"  Phone Number ID: {settings.WHATSAPP_PHONE_NUMBER_ID or 'NOT SET'}")
        self.stdout.write(f"  Admin Number: {settings.WHATSAPP_ADMIN_NUMBER or 'NOT SET'}")
        self.stdout.write(f"  API Version: {settings.WHATSAPP_API_VERSION}")
        self.stdout.write('')

    def _confirm_production_mode(self):
        """Ask for confirmation before running in production mode"""
        self.stdout.write(self.style.ERROR('⚠️  WARNING: You are testing in PRODUCTION mode!'))
        self.stdout.write(self.style.ERROR('This will send ACTUAL WhatsApp messages.'))
        confirm = input('Are you sure? (yes/no): ')
        if confirm.lower() != 'yes':
            raise CommandError('Test cancelled.')
        self.stdout.write(self.style.SUCCESS('✓ Proceeding with production test\n'))

    def _test_simulation(self, options):
        """Simulate receiving WhatsApp messages without real sending"""
        self.stdout.write(self.style.WARNING('🎭 SIMULATION MODE (No Real Messages Sent)'))
        self.stdout.write('='*70 + '\n')
        
        phone = options.get('phone', '+918074101457')
        order_id = options.get('order', 123)
        
        self.stdout.write(f'Simulating incoming WhatsApp message from customer...\n')
        
        # Create simulated message
        payload = WhatsAppMessageSimulator.simulate_order_confirmation_received(
            customer_phone=phone,
            order_id=order_id
        )
        
        # Display formatted message
        WhatsAppMessageSimulator.print_mock_message(payload)
        
        # Show raw JSON if requested
        if options['raw_json']:
            WhatsAppMessageSimulator.print_raw_json(payload)
        
        self.stdout.write(self.style.SUCCESS(
            '✅ Simulation complete! This is what a WhatsApp message would look like.\n'
        ))
        
        # Show webhook handler example
        self._show_webhook_handler_example()

    def _test_with_phone(self, phone_number, message):
        """Test sending a direct message to a phone number"""
        self.stdout.write(self.style.WARNING(f'Testing message to: {phone_number}\n'))

        client = WhatsAppClient()

        self.stdout.write(f'Message: {message}')
        self.stdout.write('')

        result = client.send_text(phone_number, message)

        self._display_result(result)

    def _test_with_order(self, order_id):
        """Test sending order notifications"""
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            raise CommandError(f'Order with ID {order_id} not found')

        self.stdout.write(self.style.WARNING(f'Testing order notifications for Order #{order_id}\n'))
        self.stdout.write(f'Customer: {order.full_name}')
        self.stdout.write(f'Email: {order.email}')
        self.stdout.write(f'Phone: {order.phone}')
        self.stdout.write(f'Total: ₹{order.total_amount}')
        self.stdout.write('')

        self.stdout.write(self.style.WARNING('Sending notifications...\n'))

        results = send_order_notifications(order)

        self.stdout.write(self.style.SUCCESS('Order ID: ' + str(results['order_id'])))
        self.stdout.write(self.style.SUCCESS('Timestamp: ' + str(results['timestamp'])))

        # Customer notification
        self.stdout.write(self.style.WARNING('\n📱 Customer Notification:'))
        self._display_notification_result(results['customer'])

        # Admin notification
        self.stdout.write(self.style.WARNING('\n👨‍💼 Admin Notification:'))
        self._display_notification_result(results['admin'])

    def _display_result(self, result):
        """Display formatted result"""
        if result['success']:
            self.stdout.write(self.style.SUCCESS('✅ SUCCESS'))
            self.stdout.write(f"  Mode: {result.get('mode', 'N/A')}")

            if result['mode'] == 'dry_run':
                self.stdout.write(f"  Status: Message logged (no API call)")
            else:
                self.stdout.write(f"  Message ID: {result.get('message_id', 'N/A')}")

            if 'payload' in result:
                self.stdout.write(f"\n  Payload:")
                payload_str = json.dumps(result['payload'], indent=4)
                for line in payload_str.split('\n'):
                    self.stdout.write(f"    {line}")
        else:
            self.stdout.write(self.style.ERROR('❌ FAILED'))
            self.stdout.write(f"  Error: {result.get('error', 'Unknown error')}")

            if 'details' in result:
                self.stdout.write(f"  Details: {result['details']}")

        self.stdout.write('')

    def _display_notification_result(self, result):
        """Display notification result"""
        recipient_type = result.get('recipient_type', 'Unknown')
        recipient = result.get('to', 'N/A')

        if result['success']:
            self.stdout.write(self.style.SUCCESS(f"  ✅ {recipient_type.capitalize()} ({recipient})"))
            self.stdout.write(f"     Mode: {result.get('mode', 'N/A')}")

            if result['mode'] == 'dry_run':
                self.stdout.write(f"     Status: Logged (no API call)")
            else:
                self.stdout.write(f"     Message ID: {result.get('message_id', 'N/A')}")
        else:
            self.stdout.write(self.style.ERROR(f"  ❌ {recipient_type.capitalize()} ({recipient})"))
            self.stdout.write(f"     Error: {result.get('error', 'Unknown error')}")

    def _show_usage(self):
        """Show usage examples"""
        self.stdout.write(self.style.WARNING('Usage:'))
        self.stdout.write('\n1. Send test message to your phone (dry-run):')
        self.stdout.write('   python manage.py test_whatsapp --phone +918074101457')

        self.stdout.write('\n2. Send order notification (dry-run):')
        self.stdout.write('   python manage.py test_whatsapp --order 123')

        self.stdout.write('\n3. Send custom message (dry-run):')
        self.stdout.write('   python manage.py test_whatsapp --phone +918074101457 --message "Custom message"')

        self.stdout.write('\n4. 🎭 SIMULATE receiving a message (No sending):')
        self.stdout.write('   python manage.py test_whatsapp --simulate --phone +918074101457')

        self.stdout.write('\n5. Show raw JSON payload of simulated message:')
        self.stdout.write('   python manage.py test_whatsapp --simulate --raw-json')

        self.stdout.write('\n6. Production mode (actual API call):')
        self.stdout.write('   python manage.py test_whatsapp --phone +918074101457 --mode production')

        self.stdout.write('\nNote: Set WHATSAPP_DRY_RUN=False in .env to enable production API calls')
        self.stdout.write('')

    def _show_webhook_handler_example(self):
        """Show example webhook handler code"""
        self.stdout.write(self.style.WARNING('📚 Webhook Handler Example:'))
        self.stdout.write('='*70 + '\n')
        
        example = '''# In your views.py, create a webhook handler:

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

@csrf_exempt
@require_http_methods(["POST", "GET"])
def whatsapp_webhook(request):
    """Webhook to receive incoming WhatsApp messages from Meta"""
    if request.method == "GET":
        # Webhook verification from Meta
        verify_token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        if verify_token == "YOUR_VERIFY_TOKEN":
            return JsonResponse({"hub.challenge": challenge})
        return JsonResponse({"error": "Invalid token"}, status=403)
    
    if request.method == "POST":
        try:
            payload = json.loads(request.body)
            
            # Get message data
            message_data = payload['entry'][0]['changes'][0]['value']['messages'][0]
            phone = message_data['from']
            message_body = message_data['text']['body']
            
            # Process message
            print(f"Received message from {phone}: {message_body}")
            
            # Your message handling logic here
            
            return JsonResponse({"status": "received"}, status=200)
        
        except Exception as e:
            print(f"Error processing webhook: {str(e)}")
            return JsonResponse({"error": str(e)}, status=400)

# In urls.py:
path("webhooks/whatsapp/", whatsapp_webhook, name="whatsapp_webhook"),
'''
        
        self.stdout.write(example)
