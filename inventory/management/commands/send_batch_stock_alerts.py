"""
Management command to send batch low stock alerts to admin
Usage: python manage.py send_batch_stock_alerts
"""
from django.core.management.base import BaseCommand
from inventory.models import Product
from inventory import utils


class Command(BaseCommand):
    help = 'Send a consolidated batch low stock alert email to admin'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sending alert even if no low stock items',
        )
        parser.add_argument(
            '--threshold',
            type=int,
            default=10,
            help='Stock threshold level (default: 10)',
        )

    def handle(self, *args, **options):
        threshold = options.get('threshold', 10)
        force = options.get('force', False)
        
        # Get all low stock products
        low_stock_products = Product.objects.filter(
            stock_quantity__lt=threshold,
            is_active=True
        ).select_related('category').order_by('stock_quantity')
        
        if not low_stock_products.exists():
            if force:
                self.stdout.write(self.style.WARNING('No low stock products found, but sending anyway (--force)'))
            else:
                self.stdout.write(self.style.SUCCESS('✅ No low stock products found - no alert needed'))
                return
        
        product_list = list(low_stock_products)
        count = len(product_list)
        
        self.stdout.write(f'Processing {count} low stock product(s)...')
        
        # Display products
        self.stdout.write(self.style.WARNING('\n📋 LOW STOCK ITEMS:'))
        self.stdout.write('-' * 80)
        for idx, product in enumerate(product_list, 1):
            shortage = threshold - product.stock_quantity
            self.stdout.write(
                f'{idx}. {product.name:<40} | '
                f'Stock: {product.stock_quantity:<3} | '
                f'Short: {shortage:<3} | '
                f'Category: {product.category.name}'
            )
        self.stdout.write('-' * 80)
        
        # Send batch alert
        self.stdout.write('\n📧 Sending consolidated batch alert email...')
        success = utils.send_batch_stock_alerts(product_list)
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ Successfully sent batch alert for {count} low stock item(s) to admin')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'\n❌ Failed to send batch alert - check logs for details')
            )
