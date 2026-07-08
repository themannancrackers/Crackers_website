import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crackers_ecommerce.settings')
django.setup()

from inventory.models import Product
from django.db import transaction

# Fetch all products sorted by category ordering, then current product_id, then database ID
products = list(Product.objects.all().order_by('category__order', 'category__name', 'product_id', 'id'))

print(f"Found {len(products)} products. Starting sequential update...")

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
            print(f"Updated: ID {product.id} | '{product.name}' -> Product ID: {new_id}")
            
    print("\n[SUCCESS] Successfully re-indexed all products starting from 1!")
except Exception as e:
    print(f"\n[ERROR] An error occurred: {e}")
