import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crackers_ecommerce.settings')
django.setup()

from inventory.models import Product
from django.db import transaction

# Fetch active products sorted by category ordering, then product order, then current product_id, then database ID
active_products = list(Product.objects.filter(is_active=True).order_by('category__order', 'category__name', 'order', 'product_id', 'id'))

# Fetch inactive products sorted by category ordering, then product order, then current product_id, then database ID
inactive_products = list(Product.objects.filter(is_active=False).order_by('category__order', 'category__name', 'order', 'product_id', 'id'))

products = active_products + inactive_products

print(f"Found {len(products)} products ({len(active_products)} active, {len(inactive_products)} inactive). Starting sequential update...")

try:
    with transaction.atomic():
        # Step 1: Assign temporary large unique values to prevent unique constraint conflicts during update
        for idx, product in enumerate(products):
            product.product_id = 999999 + idx
            product.save()

        # Step 2: Assign final sequential IDs starting from 1
        for idx, product in enumerate(products):
            new_id = idx + 1
            product.product_id = new_id
            product.save()
            print(f"Updated: ID {product.id} | '{product.name}' (Active: {product.is_active}) -> Product ID: {new_id}")
            
    print("\n[SUCCESS] Successfully re-indexed all products starting from 1!")
except Exception as e:
    print(f"\n[ERROR] An error occurred: {e}")
