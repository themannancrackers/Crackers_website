#!/usr/bin/env python
"""
Script to fix broken product image references
Maps database image paths to actual files in media/products folder
"""
import os
import django
from pathlib import Path
from difflib import SequenceMatcher

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crackers_ecommerce.settings')
django.setup()

from django.conf import settings
from inventory.models import Product

# Get all actual files in the media/products folder
media_dir = settings.MEDIA_ROOT / 'products'
actual_files = {}

print("🔍 Scanning actual files in media folder...")
if media_dir.exists():
    for file in os.listdir(media_dir):
        actual_files[file.lower()] = file
    print(f"✅ Found {len(actual_files)} files in media folder")
else:
    print(f"❌ Media folder not found: {media_dir}")
    exit(1)

# Check which products have broken image references
products = Product.objects.all()
broken = []
fixed = []
unfound = []

print("\n🔎 Checking product image references...")
for p in products:
    if not p.image:
        continue
        
    # Get filename from the path
    image_name = p.image.name.split('/')[-1] if '/' in p.image.name else p.image.name
    
    # Check if file exists (case-insensitive)
    if image_name.lower() not in actual_files:
        broken.append((p.id, p.name, p.image.name))

print(f"✅ Total products: {products.count()}")
print(f"✅ Products with images in DB: {Product.objects.filter(image__isnull=False).count()}")
print(f"⚠️  Broken image references: {len(broken)}")

if broken:
    print("\n📋 Broken references (first 10):")
    for pid, name, img_path in broken[:10]:
        print(f"  - [{pid}] {name}: {img_path}")
    
    print("\n🔧 Attempting to fix broken references...\n")
    
    # Try to match broken references with actual files
    for pid, name, img_path in broken:
        # Create a simple similarity matcher
        product_name_lower = name.lower().replace(' ', '_')
        
        # Try exact match first
        matching_file = actual_files.get(img_path.lower())
        
        # If not found, try to find similar filename
        if not matching_file:
            best_match = None
            best_ratio = 0
            
            for actual_file in actual_files.values():
                ratio = SequenceMatcher(None, product_name_lower, actual_file.lower()).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = actual_file
            
            if best_ratio > 0.5:  # If similarity is above 50%
                matching_file = best_match
        
        if matching_file:
            # Update the product's image field
            p = Product.objects.get(id=pid)
            p.image = f'products/{matching_file}'
            p.save()
            fixed.append((name, img_path, matching_file))
            print(f"✅ Fixed: {name}")
            print(f"   Old: {img_path}")
            print(f"   New: products/{matching_file}\n")
        else:
            unfound.append((pid, name, img_path))
            print(f"❌ Could not find match for: {name} ({img_path})\n")

print(f"\n{'='*60}")
print(f"SUMMARY:")
print(f"  ✅ Fixed: {len(fixed)}")
print(f"  ❌ Could not fix: {len(unfound)}")
print(f"{'='*60}")

if unfound:
    print("\n🔴 Could not find matches for these products:")
    for pid, name, img_path in unfound:
        print(f"  - [{pid}] {name}: {img_path}")